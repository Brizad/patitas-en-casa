"""Posibles duplicados de un reporte (RF-17, #75): a menos de 200 m y 2 horas.

Se calcula al pedir la cola, en Python, con la fórmula del haversine (distancia sobre la
esfera terrestre). Con pocos reportes pendientes basta; con miles convendría PostGIS
(índice espacial en la base), como dice el documento de arquitectura.
"""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from app import config
from app.dominio.modelos import EstadoReporte, Reporte

RADIO_TIERRA_M = 6_371_000


def distancia_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distancia en metros entre dos puntos (latitud, longitud) en grados."""
    lat1, lon1, lat2, lon2 = map(radians, (*a, *b))
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * RADIO_TIERRA_M * asin(sqrt(h))


def _punto(reporte: Reporte) -> tuple[float, float] | None:
    u = reporte.ubicacion
    return None if u.latitud is None or u.longitud is None else (u.latitud, u.longitud)


def posibles_duplicados(reporte: Reporte, otros: list[Reporte]) -> list[str]:
    """Códigos de los otros reportes cercanos en espacio y tiempo. Solo con GPS: dos
    direcciones escritas a mano no se pueden comparar de forma fiable. Los descartados no
    cuentan (ya se revisaron)."""
    punto = _punto(reporte)
    if punto is None:
        return []
    cercanos = []
    for otro in otros:
        otro_punto = _punto(otro)
        if (otro.codigo == reporte.codigo or otro_punto is None
                or otro.estado == EstadoReporte.DESCARTADO):
            continue
        horas = abs((otro.creado_en - reporte.creado_en).total_seconds()) / 3600
        if (horas <= config.DUPLICADO_HORAS
                and distancia_m(punto, otro_punto) <= config.DUPLICADO_METROS):
            cercanos.append(otro.codigo)
    return cercanos
