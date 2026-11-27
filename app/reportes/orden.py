"""Regla ÚNICA de orden de las bandejas del personal y de la consulta del ciudadano (#496).

1. Nivel de prioridad: urgente (crítica) > alta > normal (media y baja). Un caso sin triaje va
   según la prioridad que ya tenga el reporte (la sugerida o la de falla segura, RN-03); sin
   ninguna, normal.
2. En el mismo nivel, el más antiguo primero (orden de llegada, FIFO).
3. Un caso con más de HORAS_ATRASO sin avanzar de estado no va en la lista principal: va en
   «Atrasados».

Las funciones reciben cómo leer la prioridad, la llegada y el último avance de cada caso, así
sirven igual para reportes de la cola y para ofertas de rescate.
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from datetime import datetime, timedelta
from typing import TypeVar

from app import config
from app.dominio.modelos import Prioridad
from app.triaje.normalizacion import normalizar

T = TypeVar("T")

NIVELES = ("urgente", "alta", "normal")
_NIVEL = {Prioridad.CRITICA: "urgente", Prioridad.ALTA: "alta",
          Prioridad.MEDIA: "normal", Prioridad.BAJA: "normal"}


def nivel(prioridad: Prioridad | None) -> str:
    return _NIVEL.get(prioridad, "normal")


def atrasado(ultimo_avance: datetime, ahora: datetime) -> bool:
    return ahora - ultimo_avance > timedelta(hours=config.HORAS_ATRASO)


def ordenar(casos: Iterable[T], prioridad: Callable[[T], Prioridad | None],
            llegada: Callable[[T], datetime]) -> list[T]:
    return sorted(casos, key=lambda c: (NIVELES.index(nivel(prioridad(c))), llegada(c)))


def separar(casos: Iterable[T], prioridad: Callable[[T], Prioridad | None],
            llegada: Callable[[T], datetime], ultimo_avance: Callable[[T], datetime],
            ahora: datetime) -> tuple[list[T], list[T]]:
    """(principal, atrasados), los dos ya ordenados con la misma regla."""
    ordenados = ordenar(casos, prioridad, llegada)
    principal = [c for c in ordenados if not atrasado(ultimo_avance(c), ahora)]
    return principal, [c for c in ordenados if atrasado(ultimo_avance(c), ahora)]


def casos_antes(caso: T, casos: Iterable[T], prioridad: Callable[[T], Prioridad | None],
                llegada: Callable[[T], datetime], ultimo_avance: Callable[[T], datetime],
                ahora: datetime) -> int:
    """Cuántos casos de la lista principal van antes que este (los atrasados no cuentan)."""
    clave = (NIVELES.index(nivel(prioridad(caso))), llegada(caso))
    principal, _ = separar(casos, prioridad, llegada, ultimo_avance, ahora)
    # Comparación estricta: el propio caso (aunque llegue como otro objeto) no se cuenta.
    return sum(1 for c in principal if (NIVELES.index(nivel(prioridad(c))), llegada(c)) < clave)


# --- Datos de la tarjeta sacados de lo que ya hay (sin inventar nada) ----------------------

_PERRO = re.compile(r"\b(perr[oa]s?|perrit[oa]s?|cachorr[oa]s?|canin[oa]s?)\b", re.IGNORECASE)
_GATO = re.compile(r"\b(gat[oa]s?|gatit[oa]s?|felin[oa]s?|michis?)\b", re.IGNORECASE)
_SENAL = re.compile(r"^señal '(.+)' -> \w+$")


def especie_mencionada(descripcion: str) -> str | None:
    """«perro» o «gato» si el ciudadano lo escribió (lo primero que nombra); si no, None."""
    perro, gato = _PERRO.search(descripcion), _GATO.search(descripcion)
    if perro and (not gato or perro.start() < gato.start()):
        return "perro"
    return "gato" if gato else None


def estado_del_animal(evidencias: Iterable[str], descripcion: str) -> str | None:
    """La palabra del ciudadano donde el triaje encontró su primera señal clínica (la señal es
    una raíz: «atropellad» → «atropellado»)."""
    palabras = re.findall(r"[^\W\d_]+", descripcion)
    for evidencia in evidencias:
        senal = _SENAL.match(evidencia)
        if not senal:
            continue
        raiz = normalizar(senal.group(1))
        for palabra in palabras:
            if " " not in raiz and raiz in normalizar(palabra):
                return palabra.lower()
        return senal.group(1)  # señal de varias palabras («no respira»): tal cual
    return None
