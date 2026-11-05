"""Rutas de sesión y administración: cuentas, refugios y vínculos (DT-02, DT-06, RF-13, RF-14,
RF-16) (DT-13, #267)."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from app.api.comun import Contexto, fecha_utc
from app.api.comun import cambiar as _cambio
from app.api.seguridad import no_autenticado
from app.bitacora.repositorio import Evento
from app.dominio.modelos import (
    Refugio,
    Rol,
    Usuario,
)
from app.usuarios.contrasenas import ContrasenaInvalida
from app.usuarios.intentos import (
    clave_correo,
    clave_ip,
)
from app.usuarios.repositorio import CorreoDuplicado
from app.usuarios.servicio import (
    AutoSuspension,
    CuentaNoEncontrada,
    normalizar_correo,
)

logger = logging.getLogger("app.api.main")  # el mismo de antes: los logs no cambian


class CuentaEntrada(BaseModel):
    """#67: el administrador crea cuentas del personal (la contraseña nunca se devuelve)."""

    correo: str = Field(max_length=254)
    nombre: str = Field(max_length=120)
    rol: Rol
    contrasena: str = Field(max_length=128)


class ActivoEntrada(BaseModel):
    activo: bool


class RefugioEntrada(BaseModel):
    nombre: str = Field(max_length=120)
    capacidad: int = Field(gt=0, le=10_000)
    direccion: str = Field(default="", max_length=200)  # #108 (RF-14)


class VinculoEntrada(BaseModel):
    refugio_id: int | None  # None desvincula


def _refugio(refugio: Refugio) -> dict:
    return {"id": refugio.id, "nombre": refugio.nombre, "capacidad": refugio.capacidad,
            "ocupados": refugio.ocupados, "direccion": refugio.direccion}


def _cuenta(usuario: Usuario) -> dict:
    return {"correo": usuario.correo, "nombre": usuario.nombre, "rol": usuario.rol.value,
            "activo": usuario.activo, "refugio_id": usuario.refugio_id}


# C901: como en crear_app, mccabe suma las rutas anidadas; cada una es sencilla.
def crear_rutas_admin(ctx: Contexto) -> APIRouter:  # noqa: C901
    rutas = APIRouter()
    administracion = ctx.administracion
    emisor_tokens = ctx.emisor_tokens
    limite_intentos = ctx.limite_intentos
    repositorio_bitacora = ctx.repositorio_bitacora
    repositorio_refugios = ctx.repositorio_refugios
    repositorio_usuarios = ctx.repositorio_usuarios
    usuario_actual = ctx.usuario_actual
    usuarios = ctx.usuarios

    @rutas.post("/auth/token")
    def iniciar_sesion(formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
                       peticion: Request):
        """Inicio de sesión del personal: username = correo (DT-02).

        DT-06: con demasiados fallos recientes del correo o de la IP responde 429 sin mirar
        la contraseña, ni siquiera la correcta: así el atacante no sabe si acertó.
        """
        # La IP es la de la conexión; X-Forwarded-For no se usa porque el cliente la inventa.
        ip = peticion.client.host if peticion.client else "desconocida"
        claves = [clave_correo(normalizar_correo(formulario.username)), clave_ip(ip)]
        espera = limite_intentos.segundos_de_bloqueo(claves)
        if espera:
            # Sin correo ni contraseña en el log: solo la IP y la espera.
            logger.warning("Inicio de sesión bloqueado por intentos fallidos (IP %s, %d s).",
                           ip, espera)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Demasiados intentos fallidos. Intenta de nuevo en {espera} segundos.",
                headers={"Retry-After": str(espera)})
        usuario = usuarios.autenticar(formulario.username, formulario.password)
        if usuario is None:
            limite_intentos.registrar_fallo(claves)
            # Mismo mensaje exista o no el correo: no se revela qué cuentas existen.
            raise no_autenticado("Correo o contraseña incorrectos.")
        limite_intentos.registrar_exito(claves[0])
        # RF-16: historial de acceso de la cuenta (en la bitácora, también inmutable).
        repositorio_bitacora.registrar(Evento(usuario.correo, "inicio de sesión", {}, 200))
        return {"access_token": emisor_tokens.emitir(usuario), "token_type": "bearer",
                "expira_en": emisor_tokens.minutos * 60}

    @rutas.get("/auth/yo")
    def mi_cuenta(usuario: Usuario = usuario_actual):
        return {"correo": usuario.correo, "nombre": usuario.nombre, "rol": usuario.rol.value}

    # --- Fase 1 (#67): administración de cuentas (RF-13, RF-16) -------------------------

    @rutas.get("/admin/usuarios")
    def listar_cuentas(_admin: Usuario = administracion):
        return [_cuenta(u) for u in usuarios.listar()]

    @rutas.post("/admin/usuarios", status_code=201)
    def crear_cuenta(datos: CuentaEntrada, _admin: Usuario = administracion):
        try:
            nueva = usuarios.registrar(datos.correo, datos.nombre, datos.rol, datos.contrasena)
        except CorreoDuplicado as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except (ContrasenaInvalida, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return _cuenta(nueva)

    @rutas.put("/admin/usuarios/{correo}/activo")
    def suspender_o_reactivar(correo: str, datos: ActivoEntrada, peticion: Request,
                              admin: Usuario = administracion):
        """RF-16: una cuenta suspendida pierde el acceso en la siguiente petición, porque
        la dependencia de sesión relee la cuenta (no basta con tener un token vigente)."""
        antes = repositorio_usuarios.buscar_por_correo(normalizar_correo(correo))
        try:
            usuarios.cambiar_activo(admin, correo, datos.activo)
        except AutoSuspension as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except CuentaNoEncontrada as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        _cambio(peticion, {"activo": antes.activo}, {"activo": datos.activo})
        return {"correo": normalizar_correo(correo), "activo": datos.activo}

    @rutas.get("/admin/usuarios/{correo}/accesos")
    def historial_de_acceso(correo: str, _admin: Usuario = administracion):
        """RF-16: inicios de sesión de la cuenta, el más reciente primero."""
        return [{"momento": fecha_utc(e.momento)} for e in repositorio_bitacora.de_actor(
            normalizar_correo(correo), "inicio de sesión")]

    @rutas.get("/admin/refugios")
    def listar_refugios(_admin: Usuario = administracion):
        return [_refugio(r) for r in repositorio_refugios.todos()]

    @rutas.post("/admin/refugios", status_code=201)
    def registrar_refugio(datos: RefugioEntrada, _admin: Usuario = administracion):
        """RF-14: el refugio nace sin animales; sus cupos los usa el coordinador."""
        if not datos.nombre.strip():
            raise HTTPException(status_code=422, detail="El nombre del refugio es obligatorio.")
        return _refugio(repositorio_refugios.crear(datos.nombre.strip(), datos.capacidad,
                                                   datos.direccion.strip()))

    @rutas.put("/admin/usuarios/{correo}/refugio")
    def vincular_a_refugio(correo: str, datos: VinculoEntrada, peticion: Request,
                           _admin: Usuario = administracion):
        correo = normalizar_correo(correo)
        antes = repositorio_usuarios.buscar_por_correo(correo)
        if datos.refugio_id is not None and not repositorio_refugios.existe(datos.refugio_id):
            raise HTTPException(status_code=404, detail="Ese refugio no existe.")
        if not repositorio_usuarios.vincular_refugio(correo, datos.refugio_id):
            raise HTTPException(status_code=404, detail="No existe una cuenta con ese correo.")
        _cambio(peticion, {"refugio_id": antes.refugio_id}, {"refugio_id": datos.refugio_id})
        return {"correo": correo, "refugio_id": datos.refugio_id}

    return rutas
