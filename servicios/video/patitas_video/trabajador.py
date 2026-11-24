"""Trabajador local de video (#125): pide trabajos a la API de Render y los analiza.

Uso (en la PC del equipo, ver servicios/video/README.md):

    set PATITAS_API_URL=https://patitas-en-casa-pnnk.onrender.com
    set PATITAS_VIDEO_TOKEN=<el mismo valor que en Render>
    python -m patitas_video.trabajador

Cada ciclo: reclamar → descargar a una carpeta temporal → analizar → entregar → borrar. Si no
hay trabajos espera 15 s y, mientras siga sin haber, el doble cada vez hasta 5 min (#390: cada
consulta despertaba la base de Neon). Si la API no responde, igual. El video nunca se guarda:
se borra apenas termina, salga bien o mal (RNF-08).
"""
from __future__ import annotations

import argparse
import base64
import logging
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from patitas_video import __version__
from patitas_video.cliente import (
    ApiNoDisponible,
    ClienteApi,
    PeticionRechazada,
    TrabajoPerdido,
)

logger = logging.getLogger("patitas_video")
ESPERA_SIN_TRABAJO_S = 15
ESPERA_MAXIMA_S = 300
# Render se reinicia en cada despliegue (1 a 3 min de 502): lo ya analizado no se tira por eso.
ESPERAS_ENTREGA_S = (5, 15, 45, 120)


def _con_reintentos(accion: Callable[[], object], que: str,
                    dormir: Callable[[float], None]) -> object:
    for espera in (*ESPERAS_ENTREGA_S, None):
        try:
            return accion()
        except ApiNoDisponible as error:
            if espera is None:
                raise  # el reclamo vence y el trabajo se vuelve a ofrecer (falla segura)
            logger.warning("%s: %s; reintento en %s s", que, error, espera)
            dormir(espera)
    return None


def _fallar(cliente: ClienteApi, id_: int, motivo: str) -> None:
    """Informar un fallo nunca tumba al nodo: si la API no lo acepta, el reclamo vence solo."""
    try:
        cliente.fallar(id_, motivo)
    except (TrabajoPerdido, PeticionRechazada) as error:
        logger.warning("no se pudo informar el fallo del trabajo %s: %s", id_, error)

Analizador = Callable[[str], dict]


def procesar_uno(cliente: ClienteApi, analizar: Analizador,
                 dormir: Callable[[float], None] = time.sleep) -> bool:
    """Un ciclo. True si había un trabajo (aunque haya fallado)."""
    trabajo = cliente.reclamar()
    if trabajo is None:
        return False
    id_ = trabajo["id"]
    with tempfile.TemporaryDirectory(prefix="patitas-") as carpeta:
        ruta = Path(carpeta) / "video"
        try:
            cliente.descargar(id_, ruta)
            inicio = time.monotonic()
            resultado = analizar(str(ruta))
            logger.info("trabajo %s analizado en %.0f s: %s", id_, time.monotonic() - inicio,
                        resultado["prioridad"] or "no concluyente")
        except TrabajoPerdido as error:
            logger.warning("trabajo %s perdido: %s", id_, error)
            return True
        except ApiNoDisponible:
            raise
        except Exception as error:  # el análisis falló: se informa y la API reintenta
            logger.exception("trabajo %s falló", id_)
            _fallar(cliente, id_, f"{type(error).__name__}: {error}")
            return True
    if isinstance(resultado.get("tira"), bytes):
        resultado["tira_png_base64"] = base64.b64encode(resultado.pop("tira")).decode()
    # #231: el veterinario ve en el panel por qué no hay vista y qué versión del nodo analizó.
    medidas = resultado.setdefault("medidas", {})
    medidas["version_nodo"] = __version__
    sin_vista = _subir_vista(cliente, id_, resultado, dormir)
    if sin_vista:
        medidas["sin_vista"] = sin_vista[:200]
    try:
        _con_reintentos(lambda: cliente.entregar(id_, resultado),
                        f"entrega del trabajo {id_}", dormir)
    except TrabajoPerdido as error:  # llegó tarde: el reclamo venció y lo tomó otro
        logger.warning("resultado del trabajo %s no aceptado: %s", id_, error)
    except PeticionRechazada as error:  # 422...: repetirlo igual no sirve; que la API decida
        logger.error("resultado del trabajo %s rechazado: %s", id_, error)
        _fallar(cliente, id_, f"resultado rechazado: {error}")
    return True


def _subir_vista(cliente: ClienteApi, id_: int, resultado: dict,
                 dormir: Callable[[float], None] = time.sleep) -> str | None:
    """La vista previa es opcional (#214): ningún error al subirla frena el resultado ni tumba
    al nodo (#231), y el log dice siempre si se subió o por qué no. Devuelve ese porqué (None
    si se subió) para que también llegue al panel."""
    vista, sin_vista = resultado.pop("vista", None), resultado.pop("sin_vista", None)
    if not isinstance(vista, bytes):
        sin_vista = sin_vista or "el análisis no la generó"
        logger.warning("trabajo %s sin vista previa: %s", id_, sin_vista)
        return sin_vista
    try:  # antes del resultado: al entregarlo el trabajo se cierra
        _con_reintentos(lambda: cliente.subir_vista(id_, vista),
                        f"vista previa del trabajo {id_}", dormir)
        logger.info("vista previa del trabajo %s subida (%d KB)", id_, len(vista) // 1024)
        return None
    except Exception as error:  # 413, 415, un proxy que la bloquea, Render caído...
        logger.warning("vista previa del trabajo %s no subida: %s: %s", id_,
                       type(error).__name__, error)
        return (f"la API no aceptó la vista ({len(vista) // 1024} KB): "
                f"{type(error).__name__}: {error}")


def trabajar(cliente: ClienteApi, analizar: Analizador, una_vez: bool = False,
             dormir: Callable[[float], None] = time.sleep) -> None:
    espera = ESPERA_SIN_TRABAJO_S
    while True:
        try:
            hubo = procesar_uno(cliente, analizar)
            # #390: sin trabajo la espera crece (15 s, 30 s… hasta 5 min); con trabajo, 15 s.
            siguiente = ESPERA_SIN_TRABAJO_S if hubo else min(espera * 2, ESPERA_MAXIMA_S)
        except ApiNoDisponible as error:
            hubo = False
            espera = siguiente = min(espera * 2, ESPERA_MAXIMA_S)  # Render no responde
            logger.warning("%s; reintento en %s s", error, espera)
        except PermissionError:
            raise  # token malo: seguir no arregla nada; main() lo dice claro
        except Exception:  # un nodo que nadie mira no puede morirse por un caso raro
            hubo, siguiente = False, espera
            logger.exception("ciclo con un error inesperado; el nodo sigue")
        if una_vez:
            return
        if not hubo:
            dormir(espera)
        espera = siguiente


def main() -> None:
    argumentos = argparse.ArgumentParser(description="Trabajador local de video.")
    argumentos.add_argument("--una-vez", action="store_true", help="un solo ciclo")
    argumentos.add_argument("--video", help="analiza un archivo local y muestra el resultado")
    argumentos.add_argument("--guardar-vista", help="con --video: guarda aquí el MP4 de la "
                            "vista previa")
    opciones = argumentos.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from patitas_video.adaptadores import analizador_completo  # pesado: solo aquí

    url, token = os.environ.get("PATITAS_API_URL"), os.environ.get("PATITAS_VIDEO_TOKEN")
    if not opciones.video and (not url or not token):
        raise SystemExit("Faltan PATITAS_API_URL o PATITAS_VIDEO_TOKEN (ver README.md).")
    analizar = analizador_completo()
    try:
        if opciones.video:
            resultado = analizar(opciones.video)
            resultado.pop("tira", None)
            vista, sin_vista = resultado.pop("vista", None), resultado.pop("sin_vista", None)
            print(resultado)
            if vista is None:  # #231: decir siempre si hubo vista previa
                print(f"Vista previa: no se generó ({sin_vista}).")
            elif opciones.guardar_vista:
                Path(opciones.guardar_vista).write_bytes(vista)
                print(f"Vista previa: {len(vista) // 1024} KB, guardada en "
                      f"{opciones.guardar_vista}.")
            else:
                print(f"Vista previa: {len(vista) // 1024} KB (usa --guardar-vista archivo.mp4 "
                      "para verla).")
            return
        logger.info("nodo de video %s trabajando contra %s", __version__, url)  # sin token
        trabajar(ClienteApi(url, token), analizar, una_vez=opciones.una_vez)
    finally:
        analizar.cerrar()


if __name__ == "__main__":
    main()
