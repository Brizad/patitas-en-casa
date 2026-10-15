"""Dependencias de FastAPI para la sesión del personal (DT-02)."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.dominio.modelos import Usuario
from app.seguridad.tokens import EmisorTokens, TokenInvalido
from app.usuarios.repositorio import RepositorioUsuarios

esquema_bearer = OAuth2PasswordBearer(tokenUrl="auth/token", auto_error=False)


def no_autenticado(detalle: str = "Inicia sesión para continuar.") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detalle,
                         headers={"WWW-Authenticate": "Bearer"})


def crear_dependencia_usuario(repositorio: RepositorioUsuarios,
                              emisor: EmisorTokens) -> Callable[..., Usuario]:
    def usuario_actual(token: Annotated[str | None, Depends(esquema_bearer)]) -> Usuario:
        if not token:
            raise no_autenticado()
        try:
            sesion = emisor.validar(token)
        except TokenInvalido as error:
            raise no_autenticado("La sesión no es válida o venció.") from error
        # Se relee la cuenta: una cuenta desactivada pierde el acceso de inmediato.
        usuario = repositorio.buscar_por_correo(sesion.correo)
        if usuario is None or not usuario.activo:
            raise no_autenticado("La sesión no es válida o venció.")
        return usuario

    return usuario_actual
