"""Del video al resultado (#125, RF-03): cuadros → animal → puntos → marcha → prioridad.

1. Se toman unos 5 cuadros por segundo (RNF-02: 60 s de video en menos de 3 min).
2. MediaPipe Object Detector busca un perro o un gato y da su recuadro.
3. DeepLabCut SuperAnimal-Quadruped da los puntos del cuerpo dentro del recuadro.
4. `marcha.medir` y el clasificador dan prioridad, confianza y evidencias.

Las piezas pesadas (OpenCV, MediaPipe, DeepLabCut) entran por puertos: aquí no se importan,
así esta lógica se prueba con dobles y el CI no instala 3 GB de librerías.
Falla segura: si no se ve un perro o gato, o la calidad no alcanza, el resultado es «no
concluyente» y en Render manda el texto.
"""
from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any, Protocol

from patitas_video import marcha
from patitas_video.clasificador import ClasificadorMarcha
from patitas_video.marcha import Cuadro

FPS = 5
MAX_SEGUNDOS = 60  # RN-01
# La API da el reclamo por perdido a los 10 min (VENCIMIENTO_RECLAMO_VIDEO_S): un equipo
# lento corta antes y entrega «no concluyente» (manda el texto) con tiempo para subirlo.
MAX_SEGUNDOS_ANALISIS = 480
MIN_FRACCION_CON_ANIMAL = 0.5
ESPECIES = ("dog", "cat")  # clases COCO del detector


@dataclass(frozen=True)
class Caja:
    x: float
    y: float
    ancho: float
    alto: float
    especie: str
    puntaje: float


class LectorCuadros(Protocol):
    def cuadros(self, ruta: str, fps: float) -> Iterator[Any]:
        """Imágenes RGB, unas «fps» por segundo."""


class DetectorAnimal(Protocol):
    def detectar(self, imagen: Any) -> Caja | None:
        """El perro o gato con mayor puntaje, o None."""


class EstimadorPuntos(Protocol):
    def puntos(self, imagen: Any, caja: Caja) -> Cuadro: ...


class DibujanteTira(Protocol):
    def tira(self, muestras: list[tuple[Any, Cuadro]]) -> bytes:
        """PNG pequeño con los cuadros elegidos y sus puntos dibujados."""


class EscritorVista(Protocol):
    """Arma la vista previa del veterinario (MP4 liviano con el esqueleto dibujado)."""

    def escribir(self, imagen: Any, puntos: Cuadro | None) -> None:
        """Un cuadro; «puntos» es None si no se vio al animal en él."""

    def terminar(self) -> bytes | None:
        """El MP4 listo, o None si no cupo en el tamaño máximo."""

    def cancelar(self) -> None: ...


def _no_concluyente(motivo: str, medidas: dict | None = None) -> dict:
    return {"prioridad": None, "confianza": 0.0, "evidencias": [], "motivo": motivo,
            "medidas": medidas or {}}


class _Vista:
    """Envuelve al escritor: si falla una vez, se suelta y el análisis sigue sin vista."""

    def __init__(self, escritor: EscritorVista | None) -> None:
        self._escritor = escritor
        self._cuadros = 0
        # #231: por qué no hay vista, para que el nodo lo diga en su log.
        self.motivo = None if escritor else "ffmpeg no está instalado (sudo apt install ffmpeg)"

    def escribir(self, imagen: Any, puntos: Cuadro | None) -> None:
        if self._escritor is None:
            return
        try:
            self._escritor.escribir(imagen, puntos)
            self._cuadros += 1
        except Exception as error:
            self._escritor.cancelar()
            self._escritor = None
            self.motivo = f"ffmpeg falló al escribir: {type(error).__name__}: {error}"

    def terminar(self) -> bytes | None:
        if self._escritor is None:
            return None
        if self._cuadros == 0:
            self._escritor.cancelar()
            self.motivo = "no se pudo leer ningún cuadro del video"
            return None
        try:
            mp4 = self._escritor.terminar()
        except Exception as error:
            self._escritor.cancelar()
            self.motivo = f"ffmpeg falló al cerrar: {type(error).__name__}: {error}"
            return None
        if mp4 is None:
            self.motivo = "ffmpeg no entregó el MP4 o pasó de 5 MB"
        return mp4


def _tres_muestras(muestras: list[tuple[Any, Cuadro]]) -> list[tuple[Any, Cuadro]]:
    if len(muestras) <= 3:
        return muestras
    n = len(muestras) - 1
    return [muestras[0], muestras[n // 2], muestras[n]]


def analizar(ruta: str, lector: LectorCuadros, detector: DetectorAnimal,
             estimador: EstimadorPuntos, clasificador: ClasificadorMarcha,
             dibujante: DibujanteTira | None = None,
             escritor_vista: EscritorVista | None = None,
             reloj: Callable[[], float] = time.monotonic) -> dict:
    """Devuelve el cuerpo que espera POST /video/trabajos/{id}/resultado. Si hay vista previa,
    va en la clave «vista» (bytes); el trabajador la sube aparte. Si no la hay, «sin_vista»
    dice por qué (#231); no viaja a la API."""
    vista = _Vista(escritor_vista)
    resultado = _analizar(ruta, lector, detector, estimador, clasificador, dibujante, vista,
                          reloj)
    mp4 = vista.terminar()
    if mp4 is not None:
        resultado["vista"] = mp4
    else:
        resultado["sin_vista"] = vista.motivo
    return resultado


def _analizar(ruta: str, lector: LectorCuadros, detector: DetectorAnimal,
              estimador: EstimadorPuntos, clasificador: ClasificadorMarcha,
              dibujante: DibujanteTira | None, vista: _Vista,
              reloj: Callable[[], float] = time.monotonic) -> dict:
    inicio = reloj()
    cuadros: list[Cuadro] = []
    muestras: list[tuple[Any, Cuadro]] = []
    especies: dict[str, int] = {}
    total = 0
    for imagen in lector.cuadros(ruta, FPS):
        total += 1
        if total > MAX_SEGUNDOS * FPS:
            break
        if reloj() - inicio > MAX_SEGUNDOS_ANALISIS:
            return _no_concluyente(f"el análisis tardó más de {MAX_SEGUNDOS_ANALISIS // 60} min "
                                   "en este equipo; se atiende con la descripción")
        caja = detector.detectar(imagen)
        if caja is None or caja.especie not in ESPECIES:
            cuadros.append({})
            vista.escribir(imagen, None)
            continue
        especies[caja.especie] = especies.get(caja.especie, 0) + 1
        puntos = estimador.puntos(imagen, caja)
        cuadros.append(puntos)
        vista.escribir(imagen, puntos)
        if (sum(especies.values()) - 1) % (2 * FPS) == 0:  # uno cada 2 s: poca memoria
            muestras.append((imagen, puntos))
    con_animal = sum(especies.values())
    if total == 0:
        return _no_concluyente("no se pudo leer el video")
    if con_animal / total < MIN_FRACCION_CON_ANIMAL:
        return _no_concluyente("no se ve un perro o un gato en la mayor parte del video")
    medidas = marcha.medir(cuadros, FPS)
    if not medidas.concluyente:
        return _no_concluyente("no se ve el cuerpo completo del animal el tiempo suficiente",
                               medidas.como_dict())
    resultado = clasificador.clasificar(medidas)
    especie = "perro" if max(especies, key=especies.get) == "dog" else "gato"
    salida = {"prioridad": resultado.prioridad, "confianza": resultado.confianza,
              "evidencias": [f"se ve un {especie} en el {round(con_animal / total * 100)} % "
                             "del video", *resultado.evidencias],
              "medidas": medidas.como_dict(), "version_modelo": clasificador.version}
    if dibujante is not None:
        salida["tira"] = dibujante.tira(_tres_muestras(muestras))
    return salida
