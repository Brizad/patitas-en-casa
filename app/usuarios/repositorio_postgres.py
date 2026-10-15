"""Cuentas del personal en PostgreSQL (DT-02)."""
from __future__ import annotations

from sqlalchemy import Engine, insert, select, update
from sqlalchemy.exc import IntegrityError

from app.bd.esquema import usuarios
from app.dominio.modelos import Rol, Usuario
from app.usuarios.repositorio import CorreoDuplicado

VIOLACION_DE_UNICIDAD = "23505"  # código SQLSTATE de PostgreSQL


class RepositorioUsuariosPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def crear(self, usuario: Usuario) -> None:
        try:
            with self._motor.begin() as conexion:
                conexion.execute(insert(usuarios).values(
                    correo=usuario.correo, nombre=usuario.nombre, rol=usuario.rol.value,
                    hash_contrasena=usuario.hash_contrasena, activo=usuario.activo,
                ))
        except IntegrityError as error:
            if getattr(error.orig, "sqlstate", None) == VIOLACION_DE_UNICIDAD:
                raise CorreoDuplicado(
                    f"Ya existe una cuenta con el correo {usuario.correo}.") from error
            raise

    def buscar_por_correo(self, correo: str) -> Usuario | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(
                select(usuarios).where(usuarios.c.correo == correo)
            ).mappings().first()
        if fila is None:
            return None
        return Usuario(correo=fila["correo"], nombre=fila["nombre"], rol=Rol(fila["rol"]),
                       hash_contrasena=fila["hash_contrasena"], activo=fila["activo"])

    def actualizar_hash(self, correo: str, hash_contrasena: str) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(update(usuarios).where(usuarios.c.correo == correo)
                             .values(hash_contrasena=hash_contrasena))
