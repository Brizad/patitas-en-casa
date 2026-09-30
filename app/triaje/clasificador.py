"""Clasificador de triaje por reglas (v0) para reportes en texto.

Es la primera versión del Motor de Triaje: reglas y léxico validables por un
veterinario, antes de entrenar el modelo Transformer (incremento 2).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.dominio.modelos import Prioridad

# Léxico de señales clínicas: fragmento -> prioridad que sugiere.
LEXICO = {
    "no respira": Prioridad.CRITICA,
    "convulsion": Prioridad.CRITICA,
    "atropellad": Prioridad.CRITICA,
    "inconsciente": Prioridad.CRITICA,
    "hemorragia": Prioridad.CRITICA,
    "envenen": Prioridad.CRITICA,
    "no se para": Prioridad.ALTA,
    "no se puede parar": Prioridad.ALTA,
    "fractura": Prioridad.ALTA,
    "sangr": Prioridad.ALTA,
    "herida": Prioridad.ALTA,
    "vomit": Prioridad.MEDIA,
    "cojea": Prioridad.MEDIA,
    "desnutrid": Prioridad.MEDIA,
    "no come": Prioridad.MEDIA,
    "sarna": Prioridad.BAJA,
    "garrapata": Prioridad.BAJA,
    "abandonad": Prioridad.BAJA,
}


@dataclass
class Resultado:
    prioridad: Prioridad
    confianza: float
    evidencias: list[str]


def clasificar(texto):
    t = texto.lower()
    enc = []
    for k in LEXICO:
        i = t.find(k)
        if i == -1:
            continue
        # negación simple: "no" justo antes de la señal (excepto señales que ya la incluyen)
        antes = t[max(0, i - 4):i]
        if not k.startswith("no ") and "no " in antes:
            continue
        enc.append(k)
    if not enc:
        return Resultado(Prioridad.BAJA, 0.3, [])
    orden = [Prioridad.CRITICA, Prioridad.ALTA, Prioridad.MEDIA, Prioridad.BAJA]
    p = None
    for o in orden:
        for k in enc:
            if LEXICO[k] == o:
                p = o
                break
        if p is not None:
            break
    n = 0
    for k in enc:
        if LEXICO[k] == p:
            n = n + 1
    c = 0.5 + 0.15 * n
    if c > 0.95:
        c = 0.95
    ev = []
    for k in enc:
        ev.append(f"señal '{k}' -> {LEXICO[k].value}")
    return Resultado(p, round(c, 2), ev)
