"""Persistencia de la adopción (fase 3, #85)."""
from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from app.adopciones.modelos import (
    EstadoPublicacion,
    EstadoSolicitud,
    PerfilAdoptante,
    Publicacion,
    Solicitud,
)


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


class RepositorioAdopcionesEnMemoria:
    def __init__(self) -> None:
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
