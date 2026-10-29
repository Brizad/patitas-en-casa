"""Medidas de la marcha a partir de los puntos clave del animal (#125, RF-03).

Entrada: un cuadro por muestra (unos 5 por segundo), cada uno «punto -> (x, y, confianza)»
con los nombres de DeepLabCut SuperAnimal-Quadruped. En la imagen la «y» crece hacia abajo.
Todas las distancias se dividen por el largo del cuerpo (base del cuello a base de la cola):
así no importa si el perro está cerca o lejos de la cámara.

Cada umbral está aquí con su porqué. Son valores iniciales razonados, NO validados por
veterinarios con videos reales (DT-04): se ajustan cuando haya videos etiquetados.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass

Punto = tuple[float, float, float]
Cuadro = dict[str, Punto]

PATAS = {"front_left_paw": "delantera izquierda", "front_right_paw": "delantera derecha",
         "back_left_paw": "trasera izquierda", "back_right_paw": "trasera derecha"}
PARES = (("front_left_paw", "front_right_paw"), ("back_left_paw", "back_right_paw"))

# Un punto con menos confianza que esta se ignora (el modelo no está seguro de dónde está).
UMBRAL_PUNTO = 0.5
# Hacen falta al menos 2 s útiles (10 cuadros a 5 por segundo) y la mitad del video útil.
MIN_CUADROS = 10
MIN_FRACCION_UTIL = 0.5
# De pie: el lomo a 0,4 largos del suelo o más. Un perro echado lo tiene a ~0,15.
UMBRAL_DE_PIE = 0.4
# Una pata «sin apoyo» está a más de 0,12 largos del suelo en el 70 % de los cuadros. Al
# caminar, cada pata está en el aire menos de la mitad del tiempo.
ELEVACION_SIN_APOYO = 0.12
FRACCION_SIN_APOYO = 0.7
# Cojera: una pata se mueve 40 % menos (o más) que su par.
UMBRAL_COJERA = 0.4
MOVIMIENTO_MINIMO = 0.02  # por debajo, las patas casi no se mueven: no se compara
# Quieto: se desplaza menos de 0,05 largos de cuerpo por segundo.
UMBRAL_INMOVIL = 0.05
# Paso irregular: regularidad menor que 0,6 (variación grande entre pasos).
UMBRAL_IRREGULAR = 0.6


@dataclass(frozen=True)
class Medidas:
    cuadros_utiles: float  # fracción de cuadros con el cuerpo visible
    utiles: int  # cuántos cuadros sirvieron
    de_pie: float  # fracción de los cuadros útiles en que está de pie
    asimetria: float  # 0 = patas pareadas iguales; 1 = una no se mueve
    pata_sin_apoyo: str | None  # nombre en español de la pata que no apoya
    fraccion_sin_apoyo: float
    regularidad: float | None  # 1 = pasos idénticos; None si no camina
    desplazamiento: float  # largos de cuerpo por segundo

    @property
    def concluyente(self) -> bool:
        return self.utiles >= MIN_CUADROS and self.cuadros_utiles >= MIN_FRACCION_UTIL

    def como_dict(self) -> dict:
        return {k: (round(v, 3) if isinstance(v, float) else v)
                for k, v in self.__dict__.items()}


def _confiable(cuadro: Cuadro, nombre: str) -> Punto | None:
    punto = cuadro.get(nombre)
    return punto if punto is not None and punto[2] >= UMBRAL_PUNTO else None


def _util(cuadro: Cuadro) -> dict | None:
    """Datos normalizados de un cuadro, o None si no se ve el cuerpo."""
    cuello, cola = _confiable(cuadro, "neck_base"), _confiable(cuadro, "tail_base")
    lomo = _confiable(cuadro, "back_middle")
    patas = {p: _confiable(cuadro, p) for p in PATAS}
    patas = {p: v for p, v in patas.items() if v is not None}
    if not (cuello and cola and lomo) or len(patas) < 3:
        return None
    largo = math.dist(cuello[:2], cola[:2])
    if largo <= 0:
        return None
    suelo = max(v[1] for v in patas.values())
    return {"largo": largo, "lomo": lomo, "altura": (suelo - lomo[1]) / largo,
            "elevacion": {p: (suelo - v[1]) / largo for p, v in patas.items()}}


def _asimetria(elevaciones: dict[str, list[float]]) -> float:
    peor = 0.0
    for a, b in PARES:
        if len(elevaciones[a]) < 2 or len(elevaciones[b]) < 2:
            continue
        mov_a, mov_b = statistics.pstdev(elevaciones[a]), statistics.pstdev(elevaciones[b])
        mayor = max(mov_a, mov_b)
        if mayor > MOVIMIENTO_MINIMO:
            peor = max(peor, abs(mov_a - mov_b) / mayor)
    return peor


def _regularidad(elevaciones: dict[str, list[float]]) -> float | None:
    """1 menos la variación de los intervalos entre pasos (cada vez que la pata sube)."""
    variaciones = []
    for serie in elevaciones.values():
        if len(serie) < 3 or statistics.pstdev(serie) <= MOVIMIENTO_MINIMO / 2:
            continue
        media = statistics.fmean(serie)
        subidas = [i for i in range(1, len(serie)) if serie[i - 1] <= media < serie[i]]
        intervalos = [b - a for a, b in zip(subidas, subidas[1:], strict=False)]
        if len(intervalos) >= 2:
            variaciones.append(statistics.pstdev(intervalos) / statistics.fmean(intervalos))
    return max(0.0, 1 - statistics.fmean(variaciones)) if variaciones else None


def _desplazamiento(utiles: list[dict], fps: float) -> float:
    if len(utiles) < 2:
        return 0.0
    recorrido = sum(math.dist(a["lomo"][:2], b["lomo"][:2])
                    for a, b in zip(utiles, utiles[1:], strict=False))
    largo = statistics.fmean(u["largo"] for u in utiles)
    return recorrido / largo / ((len(utiles) - 1) / fps)


def medir(cuadros: list[Cuadro], fps: float) -> Medidas:
    utiles = [u for u in map(_util, cuadros) if u is not None]
    if not utiles:
        return Medidas(0.0, 0, 0.0, 0.0, None, 0.0, None, 0.0)
    elevaciones = {p: [u["elevacion"][p] for u in utiles if p in u["elevacion"]] for p in PATAS}
    sin_apoyo = {p: sum(e > ELEVACION_SIN_APOYO for e in serie) / len(serie)
                 for p, serie in elevaciones.items() if serie}
    peor = max(sin_apoyo, key=sin_apoyo.get)
    return Medidas(
        cuadros_utiles=len(utiles) / len(cuadros), utiles=len(utiles),
        de_pie=sum(u["altura"] >= UMBRAL_DE_PIE for u in utiles) / len(utiles),
        asimetria=_asimetria(elevaciones),
        pata_sin_apoyo=PATAS[peor] if sin_apoyo[peor] >= FRACCION_SIN_APOYO else None,
        fraccion_sin_apoyo=sin_apoyo[peor],
        regularidad=_regularidad(elevaciones),
        desplazamiento=_desplazamiento(utiles, fps))
