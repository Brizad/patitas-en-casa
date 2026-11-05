"""Lo que comparten los routers de la API (DT-13, #267).

`crear_app` arma los repositorios, los servicios y las dependencias de rol una sola vez y los
reúne en un `Contexto`. Cada módulo de rutas (`app/api/rutas_*.py`) recibe ese contexto y toma
lo que necesita; así ningún router repite treinta parámetros y las rutas no cambian.
"""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi import Request


class Contexto(SimpleNamespace):
    """Servicios, repositorios y dependencias de `crear_app`, con los mismos nombres."""


def fecha_utc(fecha: datetime | None) -> str | None:
    """D-06: toda fecha de la API sale en UTC («+00:00»). PostgreSQL devuelve la hora en la
    zona de la sesión (en Cúcuta, -05:00): es el mismo instante, pero dos formatos confunden."""
    return None if fecha is None else fecha.astimezone(UTC).isoformat()


def cambiar(peticion: Request, anterior: dict | None, nuevo: dict | None) -> None:
    """RNF-12 (#149): el endpoint deja aquí cómo estaba y cómo quedó; el middleware de la
    bitácora lo guarda junto con el actor y la ruta. Solo estados y cifras, nunca datos
    personales ni el cuerpo de la petición."""
    peticion.state.cambio = (anterior, nuevo)
