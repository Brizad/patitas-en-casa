"""Persistencia de la adopción (fase 3, #85)."""
from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from app.adopciones.modelos import PerfilAdoptante


class RepositorioAdopciones(Protocol):
    def guardar_perfil(self, perfil: PerfilAdoptante) -> None:
        """Crea o reemplaza el perfil del adoptante (uno por cuenta)."""
        ...

    def perfil(self, correo: str) -> PerfilAdoptante | None: ...


class RepositorioAdopcionesEnMemoria:
    def __init__(self) -> None:
        self._perfiles: dict[str, PerfilAdoptante] = {}

    def guardar_perfil(self, perfil: PerfilAdoptante) -> None:
        self._perfiles[perfil.correo] = replace(perfil)

    def perfil(self, correo: str) -> PerfilAdoptante | None:
        encontrado = self._perfiles.get(correo)
        return None if encontrado is None else replace(encontrado)
