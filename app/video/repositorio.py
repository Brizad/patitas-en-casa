"""Dónde viven los trabajos de video (#125). Puerto + versión en memoria para las pruebas."""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Protocol

from app.video.modelos import EstadoVideo, TrabajoVideo


class RepositorioVideos(Protocol):
    def crear(self, codigo: str, ruta: str, tamano: int, ahora: datetime) -> TrabajoVideo | None:
        """Un video por reporte: si el reporte ya tiene uno, devuelve None."""

    def buscar(self, id_: int) -> TrabajoVideo | None: ...

    def de_reporte(self, codigo: str) -> TrabajoVideo | None: ...

    def reclamar(self, ahora: datetime, vence_antes_de: datetime) -> TrabajoVideo | None:
        """Toma el pendiente más antiguo (o un enviado cuyo reclamo venció) y lo marca
        «enviado». Dos trabajadores a la vez nunca reciben el mismo."""

    def guardar(self, trabajo: TrabajoVideo) -> None: ...

    def esperando_desde_antes(self, limite: datetime) -> list[TrabajoVideo]:
        """Pendientes o enviados creados antes de «limite» (nadie los analizó a tiempo)."""


class RepositorioVideosEnMemoria:
    def __init__(self) -> None:
        self._trabajos: dict[int, TrabajoVideo] = {}

    def crear(self, codigo: str, ruta: str, tamano: int, ahora: datetime) -> TrabajoVideo | None:
        if self.de_reporte(codigo) is not None:
            return None
        trabajo = TrabajoVideo(len(self._trabajos) + 1, codigo, ruta, tamano, ahora)
        self._trabajos[trabajo.id] = trabajo
        return copy.deepcopy(trabajo)

    def buscar(self, id_: int) -> TrabajoVideo | None:
        return copy.deepcopy(self._trabajos.get(id_))

    def de_reporte(self, codigo: str) -> TrabajoVideo | None:
        return next((copy.deepcopy(t) for t in self._trabajos.values() if t.codigo == codigo),
                    None)

    def reclamar(self, ahora: datetime, vence_antes_de: datetime) -> TrabajoVideo | None:
        libres = [t for t in self._trabajos.values()
                  if t.estado == EstadoVideo.PENDIENTE
                  or (t.estado == EstadoVideo.ENVIADO and t.reclamado_en < vence_antes_de)]
        if not libres:
            return None
        trabajo = min(libres, key=lambda t: t.creado_en)
        trabajo.estado, trabajo.reclamado_en = EstadoVideo.ENVIADO, ahora
        return copy.deepcopy(trabajo)

    def guardar(self, trabajo: TrabajoVideo) -> None:
        self._trabajos[trabajo.id] = copy.deepcopy(trabajo)

    def esperando_desde_antes(self, limite: datetime) -> list[TrabajoVideo]:
        return [copy.deepcopy(t) for t in self._trabajos.values()
                if t.estado in (EstadoVideo.PENDIENTE, EstadoVideo.ENVIADO)
                and t.creado_en < limite]
