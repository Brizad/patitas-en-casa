"""Persistencia de las cuentas del personal (DT-02)."""
from __future__ import annotations

from typing import Protocol

from app.dominio.modelos import Usuario


class CorreoDuplicado(ValueError):
    pass


class RepositorioUsuarios(Protocol):
    def crear(self, usuario: Usuario) -> None:
        """Guarda una cuenta nueva; lanza CorreoDuplicado si el correo ya existe."""
        ...

    def buscar_por_correo(self, correo: str) -> Usuario | None: ...

    def actualizar_hash(self, correo: str, hash_contrasena: str) -> None: ...


class RepositorioUsuariosEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, Usuario] = {}

    def crear(self, usuario: Usuario) -> None:
        if usuario.correo in self._datos:
            raise CorreoDuplicado(f"Ya existe una cuenta con el correo {usuario.correo}.")
        self._datos[usuario.correo] = usuario

    def buscar_por_correo(self, correo: str) -> Usuario | None:
        return self._datos.get(correo)

    def actualizar_hash(self, correo: str, hash_contrasena: str) -> None:
        self._datos[correo].hash_contrasena = hash_contrasena
