"""Distancia en línea recta y tiempo aproximado de llegada (#498). Sin rutas ni tráfico: por eso
la PWA siempre dice «aprox.»."""
from __future__ import annotations

import math

RADIO_TIERRA_M = 6_371_000
VELOCIDAD_URBANA_KMH = 25  # promedio urbano fijo para el tiempo estimado
LLEGANDO_M = 300  # a menos de esto, «¡Está llegando!»
# ~50 m en grados de latitud: la posición que ve el ciudadano va redondeada a esta rejilla.
REJILLA_GRADOS = 0.00045


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d_lat, d_lon = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(d_lat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d_lon / 2) ** 2
    return 2 * RADIO_TIERRA_M * math.asin(math.sqrt(h))


def minutos_aprox(metros: float) -> int:
    """Minutos a VELOCIDAD_URBANA_KMH, como mínimo 1."""
    return max(1, round(metros / (VELOCIDAD_URBANA_KMH * 1000 / 60)))


def redondear(grados: float) -> float:
    """A la rejilla de ~50 m: el ciudadano no ve la posición exacta del rescatista."""
    return round(round(grados / REJILLA_GRADOS) * REJILLA_GRADOS, 5)


def desplazar(lat: float, lon: float, metros: float, rumbo_grados: float) -> tuple[float, float]:
    """Un punto a `metros` en el rumbo dado (aproximación plana, suficiente a escala de ciudad)."""
    rumbo = math.radians(rumbo_grados)
    d_lat = metros * math.cos(rumbo) / 111_320
    d_lon = metros * math.sin(rumbo) / (111_320 * math.cos(math.radians(lat)))
    return lat + d_lat, lon + d_lon
