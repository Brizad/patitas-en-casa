"""Trayectorias sintéticas de puntos clave de un perro (#125), para probar la marcha sin video.

Cada cuadro es un diccionario «nombre del punto -> (x, y, confianza)», como lo entrega
DeepLabCut SuperAnimal-Quadruped. En la imagen la «y» crece hacia abajo: el suelo es la «y»
más grande. El cuerpo mide 100 px (de la base del cuello a la base de la cola).
"""
from __future__ import annotations

import math

FPS = 5
SUELO = 300.0
PATAS = ("front_left_paw", "front_right_paw", "back_left_paw", "back_right_paw")
# Fases del paso: diagonales opuestas, como en el paso normal de un perro.
FASES = {"front_left_paw": 0.0, "back_right_paw": 0.0,
         "front_right_paw": math.pi, "back_left_paw": math.pi}


def caminar(segundos: float = 10, amplitud: dict[str, float] | None = None,
            levantada: str | None = None, echado: bool = False,
            velocidad: float = 100.0) -> list[dict[str, tuple[float, float, float]]]:
    """Perro que camina a «velocidad» px/s. «amplitud» cambia cuánto sube cada pata (cojera);
    «levantada» es una pata que nunca toca el suelo; «echado» pone el lomo casi en el suelo y
    lo deja quieto."""
    amplitud = {p: 15.0 for p in PATAS} | (amplitud or {})
    cuadros = []
    for k in range(int(segundos * FPS)):
        t = k / FPS
        x = 0.0 if echado else velocidad * t
        lomo = SUELO - (15 if echado else 110)
        cuadro = {"neck_base": (x + 100, lomo - 10, 0.9), "tail_base": (x, lomo - 10, 0.9),
                  "back_middle": (x + 50, lomo, 0.9)}
        for pata in PATAS:
            sube = 0.0 if echado else max(0.0, math.sin(2 * math.pi * 0.8 * t + FASES[pata]))
            y = SUELO - 25 if pata == levantada else SUELO - amplitud[pata] * sube
            cuadro[pata] = (x + (100 if pata.startswith("front") else 0), y, 0.9)
        cuadros.append(cuadro)
    return cuadros
