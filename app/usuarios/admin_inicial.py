"""Primera cuenta de administración, creada al arrancar desde variables de entorno (#67).

¿Por qué así? En el plan gratis de Render no hay consola para ejecutar
«python -m app.usuarios.crear_usuario». Sin una primera cuenta de administrador nadie podría
crear las demás. Se leen PATITAS_ADMIN_CORREO y PATITAS_ADMIN_CONTRASENA (secretos de Render,
nunca en el repositorio) y la cuenta se crea solo si todavía no existe: reiniciar el
servicio no cambia una contraseña que el administrador ya haya cambiado.
"""
from __future__ import annotations

import logging

from app.ajustes import AjustesAdmin
from app.dominio.modelos import Rol
from app.usuarios.contrasenas import ContrasenaInvalida
from app.usuarios.repositorio import CorreoDuplicado, RepositorioUsuarios
from app.usuarios.servicio import ServicioUsuarios, normalizar_correo

logger = logging.getLogger(__name__)


def crear_admin_inicial(repositorio: RepositorioUsuarios, ajustes: AjustesAdmin) -> bool:
    """True si creó la cuenta; False si faltan variables, ya existía o no es válida."""
    if not ajustes.correo or ajustes.contrasena is None:
        return False
    correo = normalizar_correo(ajustes.correo)
    if repositorio.buscar_por_correo(correo) is not None:
        return False
    try:
        ServicioUsuarios(repositorio).registrar(
            correo, ajustes.nombre, Rol.ADMINISTRADOR, ajustes.contrasena.get_secret_value())
    except CorreoDuplicado:
        return False  # otro proceso la creó al mismo tiempo
    except (ContrasenaInvalida, ValueError) as error:
        # El mensaje del error explica la regla; nunca incluye la contraseña.
        logger.warning("No se creó el administrador inicial: %s", error)
        return False
    logger.info("Administrador inicial creado: %s", correo)
    return True
