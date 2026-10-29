"""Registro y autenticación del personal (DT-02, RNF-05)."""
from __future__ import annotations

import re

from app.dominio.modelos import Rol, Usuario
from app.usuarios import contrasenas
from app.usuarios.repositorio import RepositorioUsuarios


class CuentaNoEncontrada(LookupError):
    pass


class AutoSuspension(ValueError):
    pass


PATRON_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalizar_correo(correo: str) -> str:
    return correo.strip().lower()


class ServicioUsuarios:
    def __init__(self, repositorio: RepositorioUsuarios) -> None:
        self._repositorio = repositorio

    def registrar(self, correo: str, nombre: str, rol: Rol, contrasena: str) -> Usuario:
        correo = normalizar_correo(correo)
        if not PATRON_CORREO.match(correo):
            raise ValueError("El correo no es válido.")
        if not nombre.strip():
            raise ValueError("El nombre es obligatorio.")
        contrasenas.validar_politica(contrasena)
        usuario = Usuario(correo=correo, nombre=nombre.strip(), rol=Rol(rol),
                          hash_contrasena=contrasenas.hashear(contrasena))
        self._repositorio.crear(usuario)
        return usuario

    def autenticar(self, correo: str, contrasena: str) -> Usuario | None:
        """Devuelve el usuario si correo y contraseña son correctos y la cuenta está activa."""
        usuario = self._repositorio.buscar_por_correo(normalizar_correo(correo))
        if usuario is None:
            # Mismo trabajo que con un correo real: el tiempo no revela qué correos existen.
            contrasenas.verificar(contrasenas.hash_senuelo(), contrasena)
            return None
        if not contrasenas.verificar(usuario.hash_contrasena, contrasena) or not usuario.activo:
            return None
        if contrasenas.necesita_rehash(usuario.hash_contrasena):
            nuevo = contrasenas.hashear(contrasena)
            self._repositorio.actualizar_hash(usuario.correo, nuevo)
            usuario.hash_contrasena = nuevo
        return usuario

    def listar(self) -> list[Usuario]:
        return self._repositorio.todos()

    def cambiar_activo(self, quien: Usuario, correo: str, activo: bool) -> None:
        """RF-16. Nadie se suspende a sí mismo: así nunca se pierde la última cuenta de
        administración por un clic equivocado."""
        correo = normalizar_correo(correo)
        if not activo and correo == quien.correo:
            raise AutoSuspension("No puedes suspender tu propia cuenta.")
        if not self._repositorio.cambiar_activo(correo, activo):
            raise CuentaNoEncontrada(f"No existe una cuenta con el correo {correo}.")
