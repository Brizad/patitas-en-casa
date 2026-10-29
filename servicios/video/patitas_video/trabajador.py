"""Trabajador local de video (#125): pide trabajos a la API de Render y los analiza.

Uso (en la PC del equipo, ver servicios/video/README.md):

    set PATITAS_API_URL=https://patitas-en-casa-pnnk.onrender.com
    set PATITAS_VIDEO_TOKEN=<el mismo valor que en Render>
    python -m patitas_video.trabajador

Cada ciclo: reclamar → descargar a una carpeta temporal → analizar → entregar → borrar. Si no
hay trabajos espera unos segundos (y más si la API no responde). El video nunca se guarda:
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

from patitas_video.cliente import ApiNoDisponible, ClienteApi, TrabajoPerdido

logger = logging.getLogger("patitas_video")
ESPERA_SIN_TRABAJO_S = 15
ESPERA_MAXIMA_S = 300

Analizador = Callable[[str], dict]


def procesar_uno(cliente: ClienteApi, analizar: Analizador) -> bool:
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
            cliente.fallar(id_, f"{type(error).__name__}: {error}")
            return True
    if isinstance(resultado.get("tira"), bytes):
        resultado["tira_png_base64"] = base64.b64encode(resultado.pop("tira")).decode()
    try:
        cliente.entregar(id_, resultado)
    except TrabajoPerdido as error:  # llegó tarde: el reclamo venció y lo tomó otro
        logger.warning("resultado del trabajo %s no aceptado: %s", id_, error)
    return True


def trabajar(cliente: ClienteApi, analizar: Analizador, una_vez: bool = False,
             dormir: Callable[[float], None] = time.sleep) -> None:
    espera = ESPERA_SIN_TRABAJO_S
    while True:
        try:
            hubo = procesar_uno(cliente, analizar)
            espera = ESPERA_SIN_TRABAJO_S
        except ApiNoDisponible as error:
            hubo = False
            espera = min(espera * 2, ESPERA_MAXIMA_S)  # espera creciente si Render no responde
            logger.warning("%s; reintento en %s s", error, espera)
        if una_vez:
            return
        if not hubo:
            dormir(espera)


def main() -> None:
    argumentos = argparse.ArgumentParser(description="Trabajador local de video.")
    argumentos.add_argument("--una-vez", action="store_true", help="un solo ciclo")
    argumentos.add_argument("--video", help="analiza un archivo local y muestra el resultado")
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
            print(resultado)
            return
        logger.info("trabajando contra %s", url)  # nunca se imprime el token
        trabajar(ClienteApi(url, token), analizar, una_vez=opciones.una_vez)
    finally:
        analizar.cerrar()


if __name__ == "__main__":
    main()
