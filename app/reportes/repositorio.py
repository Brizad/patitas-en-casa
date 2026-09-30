"""Persistencia de reportes. En el MVP inicial es en memoria; luego PostgreSQL."""
from __future__ import annotations

from typing import Protocol

from app.dominio.modelos import Reporte


class RepositorioReportes(Protocol):
    def guardar(self, reporte: Reporte) -> None: ...
    def buscar(self, codigo: str) -> Reporte | None: ...
    def todos(self) -> list[Reporte]: ...


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, Reporte] = {}

    def guardar(self, reporte: Reporte) -> None:
        self._datos[reporte.codigo] = reporte

    def buscar(self, codigo: str) -> Reporte | None:
        return self._datos.get(codigo)

    def todos(self) -> list[Reporte]:
        return list(self._datos.values())
