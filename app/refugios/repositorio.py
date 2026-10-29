"""Refugios registrados por el administrador (fase 1, #67, RF-14)."""
from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from app.dominio.modelos import Refugio


class RepositorioRefugios(Protocol):
    def crear(self, nombre: str, capacidad: int) -> Refugio:
        """Guarda un refugio nuevo sin animales y lo devuelve con su id."""
        ...

    def todos(self) -> list[Refugio]:
        """Todos los refugios, por id."""
        ...

    def existe(self, refugio_id: int) -> bool: ...


class RepositorioRefugiosEnMemoria:
    def __init__(self, iniciales: list[Refugio] | None = None) -> None:
        self._datos = {r.id: r for r in iniciales or []}

    def crear(self, nombre: str, capacidad: int) -> Refugio:
        refugio = Refugio(nombre, capacidad, id=max(self._datos, default=0) + 1)
        self._datos[refugio.id] = refugio
        return replace(refugio)

    def todos(self) -> list[Refugio]:
        return [replace(self._datos[i]) for i in sorted(self._datos)]

    def existe(self, refugio_id: int) -> bool:
        return refugio_id in self._datos
