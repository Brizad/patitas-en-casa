"""Clasificador de triaje por reglas (v0) para reportes en texto.

Es la primera versión del Motor de Triaje: reglas y léxico validables por un
veterinario, antes de entrenar el modelo Transformer (incremento 2).
"""
from __future__ import annotations

from dataclasses import dataclass

from app.dominio.modelos import Prioridad
from app.triaje.normalizacion import normalizar

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


ORDEN_GRAVEDAD = [Prioridad.CRITICA, Prioridad.ALTA, Prioridad.MEDIA, Prioridad.BAJA]
CONFIANZA_SIN_SENALES = 0.3
CONFIANZA_BASE = 0.5
CONFIANZA_POR_SENAL = 0.15
CONFIANZA_MAXIMA = 0.95
VENTANA_NEGACION = 4


def clasificar(texto: str) -> Resultado:
    """Sugiere una prioridad a partir de las señales clínicas del texto."""
    senales = detectar_senales(normalizar(texto))
    if not senales:
        return Resultado(Prioridad.BAJA, CONFIANZA_SIN_SENALES, [])
    prioridad = prioridad_mas_grave(senales)
    return Resultado(prioridad, calcular_confianza(senales, prioridad), describir(senales))


def detectar_senales(texto: str) -> list[str]:
    return [senal for senal in LEXICO if _aparece_sin_negacion(senal, texto)]


def _aparece_sin_negacion(senal: str, texto: str) -> bool:
    posicion = texto.find(senal)
    if posicion == -1:
        return False
    if senal.startswith("no "):
        return True  # la señal ya contiene la negación ("no respira")
    antes = texto[max(0, posicion - VENTANA_NEGACION):posicion]
    return "no " not in antes


def prioridad_mas_grave(senales: list[str]) -> Prioridad:
    return min((LEXICO[s] for s in senales), key=ORDEN_GRAVEDAD.index)


def calcular_confianza(senales: list[str], prioridad: Prioridad) -> float:
    del_mismo_nivel = sum(1 for s in senales if LEXICO[s] == prioridad)
    confianza = CONFIANZA_BASE + CONFIANZA_POR_SENAL * del_mismo_nivel
    return round(min(confianza, CONFIANZA_MAXIMA), 2)


def describir(senales: list[str]) -> list[str]:
    return [f"señal '{s}' -> {LEXICO[s].value}" for s in senales]
