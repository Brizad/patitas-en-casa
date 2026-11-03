"""RN-01: la descripción del reporte debe estar escrita con palabras, no ser teclas al azar.

Dos comprobaciones sencillas (la PWA repite las mismas en `reportar.js`):
1. al menos 4 palabras de 2 letras o más;
2. entre el 30 % y el 70 % de las letras son vocales. El español ronda el 45 %; «Jsjsisoslqmwn»
   tiene 27 % y «aaaa eeee oooo iiii» 100 %. «perro atropellado no se levanta y sangra» tiene 41 %.
"""
from __future__ import annotations

import re

from app.triaje.normalizacion import normalizar

MIN_PALABRAS = 4
MIN_PROPORCION_VOCALES = 0.30
MAX_PROPORCION_VOCALES = 0.70
MENSAJE = "Describe con palabras qué le pasa al animal."

_PALABRA = re.compile(r"[^\W\d_]{2,}")  # 2 o más letras seguidas
_VOCALES = set("aeiou")


def descripcion_con_sentido(texto: str) -> bool:
    texto = normalizar(texto)
    if len(_PALABRA.findall(texto)) < MIN_PALABRAS:
        return False
    letras = [c for c in texto if c.isalpha()]
    vocales = sum(c in _VOCALES for c in letras)
    return MIN_PROPORCION_VOCALES <= vocales / len(letras) <= MAX_PROPORCION_VOCALES
