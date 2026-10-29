"""Persistencia de la adopción (fase 3, #85)."""
from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from app.adopciones.modelos import EstadoPublicacion, PerfilAdoptante, Publicacion


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


class RepositorioAdopcionesEnMemoria:
    def __init__(self) -> None:
        self._perfiles: dict[str, PerfilAdoptante] = {}
        self._publicaciones: dict[int, Publicacion] = {}

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
