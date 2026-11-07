"""Rutas públicas del ciudadano: reportar, consultar el estado y el seguimiento por código (RF-01,
RF-11, RF-12, RF-18, HU-08) (DT-13, #267)."""
from __future__ import annotations

import math
import re
import time
from typing import Annotated

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from pydantic import BaseModel, Field

from app import config
from app.api.comun import Contexto, fecha_utc
from app.dominio.modelos import (
    Ubicacion,
)
from app.observabilidad import evento, tracer
from app.reportes.seguimiento import linea_de_tiempo, normalizar_codigo
from app.reportes.servicio import ReporteInvalido
from app.usuarios.intentos import (
    clave_reporte,
)
from app.usuarios.servicio import (
    PATRON_CORREO,
)


class ReporteEntrada(BaseModel):
    descripcion: str = Field(max_length=config.MAX_CARACTERES_DESCRIPCION)  # A-01 (#235)
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = Field(default=None, max_length=config.MAX_CARACTERES_DIRECCION)
    video_segundos: int | None = Field(default=None, ge=0)
    video_mb: float | None = Field(default=None, ge=0)
    comuna: int | None = Field(default=None, ge=1, le=10)  # HU-06: comunas de Cúcuta
    # RF-18 (#111): opcional y con autorización expresa; se guarda cifrado (RNF-08).
    contacto: str | None = Field(default=None, max_length=120)
    autoriza_contacto: bool = False


PATRON_TELEFONO = re.compile(r"^\+?\d{7,15}$")


def normalizar_contacto(contacto: str) -> str:
    """Correo en minúsculas o teléfono solo con dígitos (y «+»); si no es ninguno, error."""
    contacto = contacto.strip()
    if PATRON_CORREO.match(contacto.lower()):
        return contacto.lower()
    telefono = re.sub(r"[\s()-]", "", contacto)
    if PATRON_TELEFONO.match(telefono):
        return telefono
    raise ValueError("El contacto debe ser un correo o un teléfono.")


# RF-12 (#61): la PWA la genera al crear el reporte (32 caracteres hex) y la repite al reenviar.
ClaveIdempotencia = Annotated[str | None, Header(alias="Idempotency-Key", min_length=16,
                                                 max_length=64, pattern=r"^[A-Za-z0-9_-]+$")]


# C901: como en crear_app, mccabe suma las rutas anidadas; cada una es sencilla.
def crear_rutas_reportes(ctx: Contexto) -> APIRouter:  # noqa: C901
    rutas = APIRouter()
    ip_de = ctx.ip_de  # A-04 (#278)
    cifrador = ctx.cifrador
    limite_intentos = ctx.limite_intentos
    reportes = ctx.reportes
    repositorio = ctx.repositorio
    repositorio_rescates = ctx.repositorio_rescates

    def contar_reporte(peticion: Request) -> None:
        """A-02 (#237): 429 con Retry-After si esta IP ya mandó el máximo de reportes."""
        limite = [clave_reporte(ip_de(peticion))]
        espera = limite_intentos.segundos_de_bloqueo(limite)
        if espera:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Recibimos muchos reportes desde esta conexión. Si es una emergencia, "
                       f"intenta de nuevo en {math.ceil(espera / 60)} minutos.",
                headers={"Retry-After": str(espera)})
        limite_intentos.registrar_fallo(limite)

    @rutas.post("/reportes", status_code=201)
    def crear_reporte(datos: ReporteEntrada, respuesta: Response, peticion: Request,
                      clave: ClaveIdempotencia = None):
        """RF-01. RF-12 (#61): con Idempotency-Key, reenviar el mismo reporte devuelve el mismo
        código con 200 en vez de crear otro; sin el encabezado funciona como antes.
        A-02 (#237): máximo REPORTES_MAXIMOS_POR_IP reportes nuevos por IP en la ventana."""
        if clave is None or repositorio.buscar_por_clave(clave) is None:  # reenvío: no cuenta
            contar_reporte(peticion)
        ubicacion = Ubicacion(datos.latitud, datos.longitud, datos.direccion, datos.comuna)
        video = (datos.video_segundos, datos.video_mb)
        contacto = None
        if datos.contacto and datos.contacto.strip():
            if not datos.autoriza_contacto:
                raise HTTPException(status_code=422, detail=(
                    "Para guardar tu contacto debes autorizar que lo usemos solo para avisarte "
                    "sobre este reporte (Ley 1581 de 2012)."))
            if cifrador is None:
                raise HTTPException(status_code=422, detail="Por ahora no podemos guardar "
                                    "contactos; tu reporte se puede enviar sin él.")
            try:
                contacto = cifrador.cifrar(normalizar_contacto(datos.contacto))
            except ValueError as error:
                raise HTTPException(status_code=422, detail=str(error)) from error
        with tracer.start_as_current_span("reportes.registrar") as span:
            span.set_attribute("reporte.comuna", datos.comuna or 0)
            span.set_attribute("reporte.con_video", datos.video_segundos is not None)
            inicio = time.perf_counter()
            try:
                if clave is None:
                    r = reportes.registrar(datos.descripcion, ubicacion, *video)
                else:
                    r, nuevo = reportes.registrar_una_vez(clave, datos.descripcion, ubicacion,
                                                          *video)
                    if not nuevo:
                        respuesta.status_code = status.HTTP_200_OK
            except ReporteInvalido as error:
                span.set_attribute("reporte.resultado", "invalido")
                evento("reporte_rechazado", motivo="validacion", comuna=datos.comuna)
                raise HTTPException(status_code=422, detail=str(error)) from error
            span.set_attribute("reporte.estado", r.estado.value)
            evento("reporte_creado", codigo=r.codigo, estado=r.estado.value, comuna=datos.comuna,
                   duracion_ms=round((time.perf_counter() - inicio) * 1000, 1))
        if contacto and r.contacto_cifrado is None:
            r.contacto_cifrado = contacto
            repositorio.guardar(r)
        return {"codigo": r.codigo, "estado": r.estado.value}

    @rutas.get("/reportes/{codigo}")
    def estado_reporte(codigo: str):
        r = repositorio.buscar(normalizar_codigo(codigo))
        if r is None:
            raise HTTPException(status_code=404, detail="Código de seguimiento no encontrado.")
        return {"codigo": r.codigo, "estado": r.estado.value}

    @rutas.get("/reportes/{codigo}/seguimiento")
    def seguimiento_del_reporte(codigo: str):
        """HU-08 (público): línea de tiempo sin datos personales (RN-14)."""
        codigo = normalizar_codigo(codigo)
        reporte = repositorio.buscar(codigo)
        if reporte is None:
            raise HTTPException(status_code=404, detail="Código de seguimiento no encontrado.")
        decisiones = repositorio.decisiones(codigo)
        descarte = repositorio.descarte(codigo)
        pasos, ultimo_cambio = linea_de_tiempo(
            reporte, decisiones[-1] if decisiones else None, repositorio_rescates.vigente(codigo),
            descarte.descartado_en if descarte else None)
        return {"codigo": codigo, "ultimo_cambio": fecha_utc(ultimo_cambio),
                "pasos": [{"nombre": p.nombre, "estado": p.estado, "detalle": p.detalle,
                           "fecha": fecha_utc(p.fecha)} for p in pasos]}

    return rutas
