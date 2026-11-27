"""Rutas de sesión y administración: cuentas, refugios y vínculos (DT-02, DT-06, RF-13, RF-14,
RF-16) (DT-13, #267)."""
from __future__ import annotations

import logging
from typing import Annotated, Literal

from fastapi import (
    APIRouter,
    Depends,
    Form,
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
    ContrasenaActualIncorrecta,
    CuentaNoEncontrada,
    normalizar_correo,
)

ENCABEZADOS_DE_PROXY = ("x-forwarded-for", "x-forwarded-proto", "x-real-ip",
                        "cf-connecting-ip", "true-client-ip", "forwarded", "cf-ray")

logger = logging.getLogger("app.api.main")  # el mismo de antes: los logs no cambian


class CuentaEntrada(BaseModel):
    """#67: el administrador crea cuentas del personal (la contraseña nunca se devuelve)."""

    correo: str = Field(max_length=254)
    nombre: str = Field(max_length=120)
    rol: Rol
    contrasena: str = Field(max_length=128)


class CambioContrasena(BaseModel):
    actual: str = Field(max_length=128)
    nueva: str = Field(max_length=128)


def cambiar_contrasena(ctx: Contexto, datos: CambioContrasena, usuario: Usuario) -> dict:
    """Los fallos cuentan para el mismo candado del inicio de sesión (DT-06): con el token
    de otra persona no se puede adivinar su contraseña a fuerza de intentos."""
    clave = clave_correo(usuario.correo)
    espera = ctx.limite_intentos.segundos_de_bloqueo([clave])
    if espera:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos fallidos. Intenta de nuevo en {espera} segundos.",
            headers={"Retry-After": str(espera)})
    try:
        ctx.usuarios.cambiar_contrasena(usuario, datos.actual, datos.nueva)
    except ContrasenaActualIncorrecta as error:
        ctx.limite_intentos.registrar_fallo([clave])
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ContrasenaInvalida as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"cambiada": True}


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


Portal = Literal["adoptante", "personal"]

# #486: el mensaje solo sale con la contraseña correcta; con una incorrecta, el 401 genérico.
OTRO_PORTAL = {
    "adoptante": "Esta cuenta es del personal del refugio. Entra por «¿Trabajas en el refugio?».",
    "personal": "Esta cuenta es de adoptante. Entra por «Adoptar».",
}


def _portal_ajeno(portal: Portal | None, usuario: Usuario) -> bool:
    """El adoptante solo entra por «Adoptar» y el personal solo por «¿Trabajas en el refugio?».
    Sin portal (clientes de la API, Swagger) no se restringe: los permisos los da el rol."""
    if portal is None:
        return False
    return (usuario.rol == Rol.ADOPTANTE) != (portal == "adoptante")


def _iniciar_sesion(ctx: Contexto, formulario: OAuth2PasswordRequestForm,
                    peticion: Request, portal: Portal | None = None) -> dict:
    limite_intentos = ctx.limite_intentos
    # A-04 (#278): la IP sale de ip_del_cliente (por defecto, la de la conexión).
    ip = ctx.ip_de(peticion)
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
    usuario = ctx.usuarios.autenticar(formulario.username, formulario.password)
    if usuario is None:
        limite_intentos.registrar_fallo(claves)
        # Mismo mensaje exista o no el correo: no se revela qué cuentas existen.
        raise no_autenticado("Correo o contraseña incorrectos.")
    if _portal_ajeno(portal, usuario):
        # #486: sin token ni registro de acceso; no es un fallo de contraseña, no se cuenta.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=OTRO_PORTAL[portal])
    limite_intentos.registrar_exito(claves[0])
    # RF-16: historial de acceso de la cuenta (en la bitácora, también inmutable).
    ctx.repositorio_bitacora.registrar(Evento(usuario.correo, "inicio de sesión", {}, 200))
    # «bearer» es el tipo de token de OAuth2 (RFC 6750), no una contraseña: falso positivo B105.
    return {"access_token": ctx.emisor_tokens.emitir(usuario), "token_type": "bearer",  # nosec B105
            "expira_en": ctx.emisor_tokens.minutos * 60}


def _diagnostico_de_ip(ctx: Contexto, peticion: Request) -> dict:
    encabezados = {n: peticion.headers.get(n) for n in ENCABEZADOS_DE_PROXY
                   if peticion.headers.get(n)}
    reenvio = [x.strip() for x in peticion.headers.get("x-forwarded-for", "").split(",")
               if x.strip()]
    return {"ip_conexion": peticion.client.host if peticion.client else None,
            "x_forwarded_for": reenvio, "encabezados": encabezados,
            "ip_usada": ctx.ip_de(peticion),
            "configuracion": {"proxies_confianza": ctx.ajustes_ip.proxies_confianza,
                              "encabezado_ip": ctx.ajustes_ip.encabezado_ip}}


def _crear_cuenta(ctx: Contexto, datos: CuentaEntrada) -> dict:
    try:
        nueva = ctx.usuarios.registrar(datos.correo, datos.nombre, datos.rol, datos.contrasena)
    except CorreoDuplicado as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except (ContrasenaInvalida, ValueError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return _cuenta(nueva)


def _suspender_o_reactivar(ctx: Contexto, correo: str, datos: ActivoEntrada,
                           peticion: Request, admin: Usuario) -> dict:
    antes = ctx.repositorio_usuarios.buscar_por_correo(normalizar_correo(correo))
    try:
        ctx.usuarios.cambiar_activo(admin, correo, datos.activo)
    except AutoSuspension as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except CuentaNoEncontrada as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    _cambio(peticion, {"activo": antes.activo}, {"activo": datos.activo})
    return {"correo": normalizar_correo(correo), "activo": datos.activo}


def _registrar_refugio(ctx: Contexto, datos: RefugioEntrada) -> dict:
    if not datos.nombre.strip():
        raise HTTPException(status_code=422, detail="El nombre del refugio es obligatorio.")
    return _refugio(ctx.repositorio_refugios.crear(datos.nombre.strip(), datos.capacidad,
                                                   datos.direccion.strip()))


def _vincular_a_refugio(ctx: Contexto, correo: str, datos: VinculoEntrada,
                        peticion: Request) -> dict:
    correo = normalizar_correo(correo)
    antes = ctx.repositorio_usuarios.buscar_por_correo(correo)
    if datos.refugio_id is not None and not ctx.repositorio_refugios.existe(datos.refugio_id):
        raise HTTPException(status_code=404, detail="Ese refugio no existe.")
    if not ctx.repositorio_usuarios.vincular_refugio(correo, datos.refugio_id):
        raise HTTPException(status_code=404, detail="No existe una cuenta con ese correo.")
    _cambio(peticion, {"refugio_id": antes.refugio_id}, {"refugio_id": datos.refugio_id})
    return {"correo": correo, "refugio_id": datos.refugio_id}


def crear_rutas_admin(ctx: Contexto) -> APIRouter:
    rutas = APIRouter()
    _rutas_de_sesion(rutas, ctx)
    _rutas_de_cuentas_y_refugios(rutas, ctx)
    return rutas


def _rutas_de_sesion(rutas: APIRouter, ctx: Contexto) -> None:
    administracion = ctx.administracion
    usuario_actual = ctx.usuario_actual

    @rutas.post("/auth/token")
    def iniciar_sesion(formulario: Annotated[OAuth2PasswordRequestForm, Depends()],
                       peticion: Request, portal: Annotated[Portal | None, Form()] = None):
        """Inicio de sesión: username = correo (DT-02).

        DT-06: con demasiados fallos recientes del correo o de la IP responde 429 sin mirar
        la contraseña, ni siquiera la correcta: así el atacante no sabe si acertó.

        #486: `portal` (adoptante | personal) es la puerta por la que se entra; si el rol no
        es de esa puerta, 403 sin token.
        """
        return _iniciar_sesion(ctx, formulario, peticion, portal)

    @rutas.get("/auth/yo")
    def mi_cuenta(usuario: Usuario = usuario_actual):
        return {"correo": usuario.correo, "nombre": usuario.nombre, "rol": usuario.rol.value}

    @rutas.post("/auth/contrasena")
    def cambiar_mi_contrasena(datos: CambioContrasena, usuario: Usuario = usuario_actual):
        """Cada persona cambia su propia contraseña dando la actual (ASVS 2.1.5, 2.1.6). Las
        sesiones ya abiertas siguen hasta que su token venza (30 minutos como máximo)."""
        return cambiar_contrasena(ctx, datos, usuario)

    # A-04 / DT-11 (#278): para ver en producción qué encabezados de proxy llegan y elegir
    # PATITAS_ENCABEZADO_IP o PATITAS_PROXIES_CONFIANZA. Solo estos encabezados: nunca
    # cookies, tokens ni el resto de la petición.
    @rutas.get("/admin/diagnostico/ip")
    def diagnostico_de_ip(peticion: Request, _admin: Usuario = administracion):
        return _diagnostico_de_ip(ctx, peticion)


def _rutas_de_cuentas_y_refugios(rutas: APIRouter, ctx: Contexto) -> None:
    administracion = ctx.administracion
    repositorio_bitacora = ctx.repositorio_bitacora
    repositorio_refugios = ctx.repositorio_refugios
    usuarios = ctx.usuarios

    # --- Fase 1 (#67): administración de cuentas (RF-13, RF-16) -------------------------

    @rutas.get("/admin/usuarios")
    def listar_cuentas(_admin: Usuario = administracion):
        return [_cuenta(u) for u in usuarios.listar()]

    @rutas.post("/admin/usuarios", status_code=201)
    def crear_cuenta(datos: CuentaEntrada, _admin: Usuario = administracion):
        return _crear_cuenta(ctx, datos)

    @rutas.put("/admin/usuarios/{correo}/activo")
    def suspender_o_reactivar(correo: str, datos: ActivoEntrada, peticion: Request,
                              admin: Usuario = administracion):
        """RF-16: una cuenta suspendida pierde el acceso en la siguiente petición, porque
        la dependencia de sesión relee la cuenta (no basta con tener un token vigente)."""
        return _suspender_o_reactivar(ctx, correo, datos, peticion, admin)

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
        return _registrar_refugio(ctx, datos)

    @rutas.put("/admin/usuarios/{correo}/refugio")
    def vincular_a_refugio(correo: str, datos: VinculoEntrada, peticion: Request,
                           _admin: Usuario = administracion):
        return _vincular_a_refugio(ctx, correo, datos, peticion)
