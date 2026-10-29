"""Persistencia de la adopción (fase 3, #85)."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Protocol

from app.adopciones.modelos import (
    EstadoPublicacion,
    EstadoSolicitud,
    PerfilAdoptante,
    Publicacion,
    Seguimiento,
    Solicitud,
)
from app.cupos.repositorio import RepositorioCupos
from app.dominio.modelos import MotivoEgreso


class RepositorioAdopciones(Protocol):
    def guardar_perfil(self, perfil: PerfilAdoptante) -> None:
        """Crea o reemplaza el perfil del adoptante (uno por cuenta)."""
        ...

    def perfil(self, correo: str) -> PerfilAdoptante | None: ...

    def publicar(self, publicacion: Publicacion) -> bool:
        """RF-25. False si el animal ya tiene una publicación (una por animal)."""
        ...

    def publicacion(self, animal_id: int) -> Publicacion | None: ...

    def disponibles(self) -> list[Publicacion]:
        """Catálogo público: publicaciones disponibles, la más antigua primero."""
        ...

    def crear_solicitud(self, solicitud: Solicitud) -> bool:
        """Asigna solicitud.id. False si el adoptante ya tiene una pendiente por ese animal."""
        ...

    def solicitudes(self) -> list[Solicitud]:
        """Todas, la más antigua primero."""
        ...

    def solicitud(self, solicitud_id: int) -> Solicitud | None: ...

    def rechazar(self, solicitud_id: int, por: str, razon: str, momento: datetime) -> bool:
        """False si ya no estaba pendiente."""
        ...

    def aprobar(self, solicitud_id: int, por: str, momento: datetime,
                seguimientos: list[Seguimiento]) -> bool:
        """Todo o nada: aprueba, rechaza las otras pendientes del animal, marca la
        publicación adoptada, da el egreso por adopción (libera el cupo, RF-26) y programa
        los seguimientos (RF-10). False si ya no estaba pendiente o el animal ya tenía una
        adopción aprobada (RN-11)."""
        ...

    def seguimientos(self, solicitud_id: int) -> list[Seguimiento]: ...


class RepositorioAdopcionesEnMemoria:
    def __init__(self, cupos: RepositorioCupos | None = None) -> None:
        self._cupos = cupos  # para el egreso al aprobar
        self._seguimientos: list[Seguimiento] = []
        self._perfiles: dict[str, PerfilAdoptante] = {}
        self._publicaciones: dict[int, Publicacion] = {}
        self._solicitudes: list[Solicitud] = []

    def guardar_perfil(self, perfil: PerfilAdoptante) -> None:
        self._perfiles[perfil.correo] = replace(perfil)

    def perfil(self, correo: str) -> PerfilAdoptante | None:
        encontrado = self._perfiles.get(correo)
        return None if encontrado is None else replace(encontrado)

    def publicar(self, publicacion: Publicacion) -> bool:
        if publicacion.animal_id in self._publicaciones:
            return False
        self._publicaciones[publicacion.animal_id] = replace(publicacion)
        return True

    def publicacion(self, animal_id: int) -> Publicacion | None:
        encontrada = self._publicaciones.get(animal_id)
        return None if encontrada is None else replace(encontrada)

    def disponibles(self) -> list[Publicacion]:
        return sorted((replace(p) for p in self._publicaciones.values()
                       if p.estado == EstadoPublicacion.DISPONIBLE),
                      key=lambda p: p.publicado_en)

    def crear_solicitud(self, solicitud: Solicitud) -> bool:
        if any(s.animal_id == solicitud.animal_id and s.adoptante == solicitud.adoptante
               and s.estado == EstadoSolicitud.PENDIENTE for s in self._solicitudes):
            return False
        solicitud.id = len(self._solicitudes) + 1
        self._solicitudes.append(replace(solicitud))
        return True

    def solicitudes(self) -> list[Solicitud]:
        return [replace(s) for s in self._solicitudes]

    def solicitud(self, solicitud_id: int) -> Solicitud | None:
        return next((replace(s) for s in self._solicitudes if s.id == solicitud_id), None)

    def _decidir(self, s: Solicitud, estado: EstadoSolicitud, por: str, momento: datetime,
                 razon: str | None) -> None:
        s.estado, s.decidida_por, s.decidida_en, s.razon = estado, por, momento, razon

    def rechazar(self, solicitud_id: int, por: str, razon: str, momento: datetime) -> bool:
        s = next((s for s in self._solicitudes if s.id == solicitud_id), None)
        if s is None or s.estado != EstadoSolicitud.PENDIENTE:
            return False
        self._decidir(s, EstadoSolicitud.RECHAZADA, por, momento, razon)
        return True

    def aprobar(self, solicitud_id: int, por: str, momento: datetime,
                seguimientos: list[Seguimiento]) -> bool:
        s = next((s for s in self._solicitudes if s.id == solicitud_id), None)
        if s is None or s.estado != EstadoSolicitud.PENDIENTE or any(
                o.animal_id == s.animal_id and o.estado == EstadoSolicitud.APROBADA
                for o in self._solicitudes):
            return False
        self._decidir(s, EstadoSolicitud.APROBADA, por, momento, None)
        for otra in self._solicitudes:
            if otra.animal_id == s.animal_id and otra.estado == EstadoSolicitud.PENDIENTE:
                self._decidir(otra, EstadoSolicitud.RECHAZADA, por, momento,
                              "Se aprobó otra solicitud para este animal.")
        self._publicaciones[s.animal_id].estado = EstadoPublicacion.ADOPTADO
        if self._cupos is not None:
            self._cupos.egresar(s.animal_id, MotivoEgreso.ADOPCION)
        for i, seguimiento in enumerate(seguimientos, start=len(self._seguimientos) + 1):
            seguimiento.id = i
            self._seguimientos.append(replace(seguimiento))
        return True

    def seguimientos(self, solicitud_id: int) -> list[Seguimiento]:
        return [replace(x) for x in self._seguimientos if x.solicitud_id == solicitud_id]
