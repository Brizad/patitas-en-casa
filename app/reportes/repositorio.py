"""Persistencia de reportes. En el MVP inicial es en memoria; luego PostgreSQL."""
from __future__ import annotations

import threading
from typing import Protocol

from app.dominio.modelos import DecisionTriaje, EstadoReporte, Reporte


class RepositorioReportes(Protocol):
    def guardar(self, reporte: Reporte) -> None: ...
    def buscar(self, codigo: str) -> Reporte | None: ...
    def todos(self) -> list[Reporte]: ...

    def confirmar(self, decision: DecisionTriaje) -> bool:
        """HU-02: si el reporte no está confirmado, lo confirma con la prioridad final y guarda
        la decisión, todo en una sola operación. False si ya estaba confirmado."""
        ...

    def decisiones(self, codigo: str) -> list[DecisionTriaje]: ...


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, Reporte] = {}
        self._decisiones: dict[str, list[DecisionTriaje]] = {}
        self._candado = threading.Lock()

    def guardar(self, reporte: Reporte) -> None:
        self._datos[reporte.codigo] = reporte

    def buscar(self, codigo: str) -> Reporte | None:
        return self._datos.get(codigo)

    def todos(self) -> list[Reporte]:
        return list(self._datos.values())

    def confirmar(self, decision: DecisionTriaje) -> bool:
        with self._candado:
            reporte = self._datos.get(decision.codigo)
            if reporte is None or reporte.estado == EstadoReporte.CONFIRMADO:
                return False
            reporte.prioridad = decision.prioridad_final
            reporte.estado = EstadoReporte.CONFIRMADO
            self._decisiones.setdefault(decision.codigo, []).append(decision)
            return True

    def decisiones(self, codigo: str) -> list[DecisionTriaje]:
        return list(self._decisiones.get(codigo, []))
