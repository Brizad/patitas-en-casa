"""Persistencia de reportes. En el MVP inicial es en memoria; luego PostgreSQL."""
from __future__ import annotations

import threading
from collections.abc import Sequence
from typing import Protocol

from app.avisos.modelos import AvisoNuevo
from app.avisos.repositorio import RepositorioAvisosEnMemoria
from app.dominio.modelos import DECIDIDOS, DecisionTriaje, Descarte, EstadoReporte, Reporte


class RepositorioReportes(Protocol):
    def guardar(self, reporte: Reporte) -> None: ...
    def buscar(self, codigo: str) -> Reporte | None: ...
    def todos(self) -> list[Reporte]: ...

    def confirmar(self, decision: DecisionTriaje, avisos: Sequence[AvisoNuevo] = ()) -> bool:
        """HU-02: si el reporte no está confirmado, lo confirma con la prioridad final y guarda
        la decisión y sus avisos pendientes (#63), todo en una sola operación. False si ya
        estaba confirmado (y entonces no guarda avisos)."""
        ...

    def decisiones(self, codigo: str) -> list[DecisionTriaje]: ...

    def descartar(self, descarte: Descarte) -> bool:
        """D-02: marca el reporte descartado y guarda el descarte, en una operación. False si
        ya estaba confirmado o descartado."""
        ...

    def descarte(self, codigo: str) -> Descarte | None: ...

    def guardar_con_clave(self, reporte: Reporte, clave: str) -> Reporte:
        """RF-12 (#61): guarda el reporte ligado a la clave de idempotencia de la PWA. Si la
        clave ya tiene un reporte, no guarda nada y devuelve ese (el reenvío no duplica)."""
        ...

    def buscar_por_clave(self, clave: str) -> Reporte | None: ...


class RepositorioEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, Reporte] = {}
        self._decisiones: dict[str, list[DecisionTriaje]] = {}
        self._descartes: dict[str, Descarte] = {}
        self._claves: dict[str, str] = {}  # clave de idempotencia -> código
        self._candado = threading.Lock()
        self.avisos = RepositorioAvisosEnMemoria()  # #63: la «misma base» de los avisos

    def guardar(self, reporte: Reporte) -> None:
        self._datos[reporte.codigo] = reporte

    def buscar(self, codigo: str) -> Reporte | None:
        return self._datos.get(codigo)

    def todos(self) -> list[Reporte]:
        return list(self._datos.values())

    def confirmar(self, decision: DecisionTriaje, avisos: Sequence[AvisoNuevo] = ()) -> bool:
        with self._candado:
            reporte = self._datos.get(decision.codigo)
            if reporte is None or reporte.estado in DECIDIDOS:
                return False
            reporte.prioridad = decision.prioridad_final
            reporte.estado = EstadoReporte.CONFIRMADO
            self._decisiones.setdefault(decision.codigo, []).append(decision)
            self.avisos.agregar(decision.codigo, avisos, decision.decidido_en)
            return True

    def decisiones(self, codigo: str) -> list[DecisionTriaje]:
        return list(self._decisiones.get(codigo, []))

    def descartar(self, descarte: Descarte) -> bool:
        with self._candado:
            reporte = self._datos.get(descarte.codigo)
            if reporte is None or reporte.estado in DECIDIDOS:
                return False
            reporte.estado = EstadoReporte.DESCARTADO
            self._descartes[descarte.codigo] = descarte
            return True

    def descarte(self, codigo: str) -> Descarte | None:
        return self._descartes.get(codigo)

    def guardar_con_clave(self, reporte: Reporte, clave: str) -> Reporte:
        with self._candado:
            if clave in self._claves:
                return self._datos[self._claves[clave]]
            self._claves[clave] = reporte.codigo
            self._datos[reporte.codigo] = reporte
            return reporte

    def buscar_por_clave(self, clave: str) -> Reporte | None:
        codigo = self._claves.get(clave)
        return None if codigo is None else self._datos.get(codigo)
