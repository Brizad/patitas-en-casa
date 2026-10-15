"""Persistencia de rescates y disponibilidad de rescatistas (HU-06, RN-08)."""
from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime
from typing import Protocol

from app.dominio.modelos import EstadoRescate, Rescate, ResultadoRescate

ACTIVOS = (EstadoRescate.EN_CAMINO, EstadoRescate.EN_SITIO)


class RescateTomado(Exception):
    """RN-08: el rescate ya tiene rescatista."""


class RescatistaOcupado(Exception):
    """RN-08: el rescatista ya tiene un rescate activo."""


class RepositorioRescates(Protocol):
    def poner_disponible(self, rescatista: str, disponible: bool) -> None: ...
    def esta_disponible(self, rescatista: str) -> bool: ...

    def aceptar(self, codigo: str, rescatista: str, momento: datetime) -> Rescate:
        """Asigna el rescate en una sola operación; lanza RescateTomado o RescatistaOcupado."""
        ...

    def vigente(self, codigo: str) -> Rescate | None:
        """El rescate en curso o atendido del reporte (los liberados no cuentan)."""
        ...

    def activo_de(self, rescatista: str) -> Rescate | None: ...
    def codigos_tomados(self) -> set[str]: ...

    def avanzar(self, codigo: str, rescatista: str, desde: EstadoRescate,
                hasta: EstadoRescate, momento: datetime,
                resultado: ResultadoRescate | None = None) -> bool:
        """Cambia de estado solo si el rescate es de ese rescatista y está en «desde»."""
        ...


class RepositorioRescatesEnMemoria:
    def __init__(self) -> None:
        self._disponibles: set[str] = set()
        self._vigentes: dict[str, Rescate] = {}  # código -> rescate no liberado
        self._candado = threading.Lock()

    def poner_disponible(self, rescatista: str, disponible: bool) -> None:
        (self._disponibles.add if disponible else self._disponibles.discard)(rescatista)

    def esta_disponible(self, rescatista: str) -> bool:
        return rescatista in self._disponibles

    def aceptar(self, codigo: str, rescatista: str, momento: datetime) -> Rescate:
        with self._candado:
            if codigo in self._vigentes:
                raise RescateTomado(codigo)
            if self._activo(rescatista) is not None:
                raise RescatistaOcupado(rescatista)
            rescate = Rescate(codigo=codigo, rescatista=rescatista,
                              estado=EstadoRescate.EN_CAMINO, aceptado_en=momento,
                              actualizado_en=momento)
            self._vigentes[codigo] = rescate
            return replace(rescate)

    def vigente(self, codigo: str) -> Rescate | None:
        rescate = self._vigentes.get(codigo)
        return replace(rescate) if rescate else None

    def _activo(self, rescatista: str) -> Rescate | None:
        return next((r for r in self._vigentes.values()
                     if r.rescatista == rescatista and r.estado in ACTIVOS), None)

    def activo_de(self, rescatista: str) -> Rescate | None:
        rescate = self._activo(rescatista)
        return replace(rescate) if rescate else None

    def codigos_tomados(self) -> set[str]:
        return set(self._vigentes)

    def avanzar(self, codigo: str, rescatista: str, desde: EstadoRescate,
                hasta: EstadoRescate, momento: datetime,
                resultado: ResultadoRescate | None = None) -> bool:
        with self._candado:
            rescate = self._vigentes.get(codigo)
            if rescate is None or rescate.rescatista != rescatista or rescate.estado != desde:
                return False
            if hasta == EstadoRescate.LIBERADO:
                del self._vigentes[codigo]
                return True
            rescate.estado, rescate.resultado, rescate.actualizado_en = hasta, resultado, momento
            return True
