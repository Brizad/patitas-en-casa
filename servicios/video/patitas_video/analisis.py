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

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Protocol

from patitas_video import marcha
from patitas_video.clasificador import ClasificadorMarcha
from patitas_video.marcha import Cuadro

FPS = 5
MAX_SEGUNDOS = 60  # RN-01
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


def _no_concluyente(motivo: str, medidas: dict | None = None) -> dict:
    return {"prioridad": None, "confianza": 0.0, "evidencias": [], "motivo": motivo,
            "medidas": medidas or {}}


def _tres_muestras(muestras: list[tuple[Any, Cuadro]]) -> list[tuple[Any, Cuadro]]:
    if len(muestras) <= 3:
        return muestras
    n = len(muestras) - 1
    return [muestras[0], muestras[n // 2], muestras[n]]


def analizar(ruta: str, lector: LectorCuadros, detector: DetectorAnimal,
             estimador: EstimadorPuntos, clasificador: ClasificadorMarcha,
             dibujante: DibujanteTira | None = None) -> dict:
    """Devuelve el cuerpo que espera POST /video/trabajos/{id}/resultado."""
    cuadros: list[Cuadro] = []
    muestras: list[tuple[Any, Cuadro]] = []
    especies: dict[str, int] = {}
    total = 0
    for imagen in lector.cuadros(ruta, FPS):
        total += 1
        if total > MAX_SEGUNDOS * FPS:
            break
        caja = detector.detectar(imagen)
        if caja is None or caja.especie not in ESPECIES:
            cuadros.append({})
            continue
        especies[caja.especie] = especies.get(caja.especie, 0) + 1
        puntos = estimador.puntos(imagen, caja)
        cuadros.append(puntos)
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
