"""Contraseñas con Argon2id (RNF-05). Solo se guarda el hash, nunca la contraseña."""
from __future__ import annotations

from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

# Valores por defecto de argon2-cffi: Argon2id con el perfil recomendado por RFC 9106.
_hasher = PasswordHasher()

MIN_CARACTERES = 12
MAX_CARACTERES = 128  # evita que una contraseña gigante se use para saturar el servidor


class ContrasenaInvalida(ValueError):
    pass


def validar_politica(contrasena: str) -> None:
    if not MIN_CARACTERES <= len(contrasena) <= MAX_CARACTERES:
        raise ContrasenaInvalida(
            f"La contraseña debe tener entre {MIN_CARACTERES} y {MAX_CARACTERES} caracteres."
        )


def hashear(contrasena: str) -> str:
    return _hasher.hash(contrasena)


def verificar(hash_guardado: str, contrasena: str) -> bool:
    try:
        return _hasher.verify(hash_guardado, contrasena)
    except (VerificationError, InvalidHashError):
        return False


def necesita_rehash(hash_guardado: str) -> bool:
    """True si el hash se hizo con parámetros más débiles que los actuales."""
    return _hasher.check_needs_rehash(hash_guardado)


@cache
def hash_senuelo() -> str:
    """Hash que se verifica cuando el correo no existe, para tardar lo mismo que con uno real."""
    return hashear("senuelo-para-tiempo-constante")
