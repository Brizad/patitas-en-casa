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


# C901: como en crear_app, mccabe suma las rutas anidadas; cada una es sencilla.
def crear_rutas_admin(ctx: Contexto) -> APIRouter:  # noqa: C901
    rutas = APIRouter()
    ip_de = ctx.ip_de  # A-04 (#278)
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
        # A-04 (#278): la IP sale de ip_del_cliente (por defecto, la de la conexión).
        ip = ip_de(peticion)
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
        # «bearer» es el tipo de token de OAuth2 (RFC 6750), no una contraseña: falso positivo B105.
        return {"access_token": emisor_tokens.emitir(usuario), "token_type": "bearer",  # nosec B105
                "expira_en": emisor_tokens.minutos * 60}

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
        encabezados = {n: peticion.headers.get(n) for n in ENCABEZADOS_DE_PROXY
                       if peticion.headers.get(n)}
        reenvio = [x.strip() for x in peticion.headers.get("x-forwarded-for", "").split(",")
                   if x.strip()]
        return {"ip_conexion": peticion.client.host if peticion.client else None,
                "x_forwarded_for": reenvio, "encabezados": encabezados,
                "ip_usada": ip_de(peticion),
                "configuracion": {"proxies_confianza": ctx.ajustes_ip.proxies_confianza,
                                  "encabezado_ip": ctx.ajustes_ip.encabezado_ip}}

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
