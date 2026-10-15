"""Tokens de sesión JWT firmados con HS256 (DT-02).

El token dice quién es la persona (sub = correo) y vence pronto (exp). La firma con la clave
secreta impide modificarlo: si alguien cambia el rol dentro del token, la firma ya no coincide.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.ajustes import MIN_CARACTERES_SECRETO_JWT
from app.dominio.modelos import Rol, Usuario

ALGORITMO = "HS256"
EMISOR = "patitas-en-casa"


class TokenInvalido(Exception):
    pass


@dataclass(frozen=True)
class Sesion:
    correo: str
    rol: Rol


class EmisorTokens:
    def __init__(self, secreto: str, minutos: int = 30,
                 reloj: Callable[[], datetime] | None = None) -> None:
        if len(secreto) < MIN_CARACTERES_SECRETO_JWT:
            raise ValueError(
                f"La clave de firma debe tener al menos {MIN_CARACTERES_SECRETO_JWT} caracteres.")
        self._secreto = secreto
        self.minutos = minutos
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def emitir(self, usuario: Usuario) -> str:
        ahora = self._reloj()
        datos = {"sub": usuario.correo, "rol": usuario.rol.value, "iss": EMISOR,
                 "iat": ahora, "exp": ahora + timedelta(minutes=self.minutos)}
        return jwt.encode(datos, self._secreto, algorithm=ALGORITMO)

    def validar(self, token: str) -> Sesion:
        """Exige firma válida con HS256 (rechaza 'none'), vigencia, emisor y datos completos."""
        try:
            datos = jwt.decode(token, self._secreto, algorithms=[ALGORITMO], issuer=EMISOR,
                               options={"require": ["sub", "rol", "iss", "iat", "exp"]})
            return Sesion(correo=datos["sub"], rol=Rol(datos["rol"]))
        except (jwt.PyJWTError, ValueError) as error:
            raise TokenInvalido("Token inválido o vencido.") from error
