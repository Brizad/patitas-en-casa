"""Rutas del video del reporte (#125, RF-03, RF-19, RNF-02).

- El ciudadano sube el video con la misma clave con la que creó el reporte (sin cuenta).
- El trabajador local (en la PC del equipo) reclama trabajos, descarga el video y devuelve el
  resultado. Se identifica con `X-Video-Token` = PATITAS_VIDEO_TOKEN; sin ese token
  configurado, el análisis de video está apagado y todo funciona como antes (manda el texto).
- El personal ve el resultado y la tira de cuadros; el ciudadano nunca (RN-14).
"""
from __future__ import annotations

import base64
import binascii
import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app import config
from app.api.comun import fecha_utc
from app.dominio.modelos import Prioridad
from app.video.almacen import MAX_BYTES, AlmacenEnDisco, AlmacenEnPostgres, ArchivoInvalido
from app.video.modelos import ResultadoVideo, TrabajoVideo
from app.video.servicio import ServicioVideo, VideoRechazado

MAX_TIRA = 200 * 1024


class ResultadoEntrada(BaseModel):
    prioridad: Prioridad | None = None  # None = no concluyente
    confianza: float = Field(0.0, ge=0, le=1)
    evidencias: list[Annotated[str, Field(max_length=200)]] = Field([], max_length=12)
    medidas: dict[str, float | int | str | None] = Field({}, max_length=20)
    version_modelo: str | None = Field(None, max_length=40)
    motivo: str | None = Field(None, max_length=300)
    tira_png_base64: str | None = Field(None, max_length=MAX_TIRA * 4 // 3 + 4)


class FalloEntrada(BaseModel):
    motivo: str = Field(min_length=1, max_length=300)


def _resultado(datos: ResultadoEntrada) -> ResultadoVideo:
    if datos.prioridad is not None and len(datos.evidencias) < 3:
        raise HTTPException(422, "Un resultado con prioridad necesita al menos 3 evidencias "
                                 "(RNF-09).")
    tira = None
    if datos.tira_png_base64:
        try:
            tira = base64.b64decode(datos.tira_png_base64, validate=True)
        except binascii.Error as error:
            raise HTTPException(422, "La tira no está en base64.") from error
        if not tira.startswith(b"\x89PNG\r\n\x1a\n") or len(tira) > MAX_TIRA:
            raise HTTPException(422, "La tira debe ser un PNG de 200 KB o menos.")
    return ResultadoVideo(datos.prioridad, datos.confianza, datos.evidencias, datos.medidas,
                          datos.version_modelo, datos.motivo, tira)


def vista_para_personal(t: TrabajoVideo) -> dict:
    return {"estado": t.estado.value, "prioridad": t.prioridad.value if t.prioridad else None,
            "confianza": t.confianza, "evidencias": t.evidencias, "medidas": t.medidas,
            "discrepancia": t.discrepancia, "motivo": t.motivo,
            "version_modelo": t.version_modelo, "tiene_tira": t.tira is not None,
            "tiene_vista": t.vista_ruta is not None}


Almacen = AlmacenEnDisco | AlmacenEnPostgres


def _ejecutar(funcion, *argumentos):
    try:
        return funcion(*argumentos)
    except VideoRechazado as error:
        raise HTTPException(error.estado_http, str(error)) from error


def _dependencia_del_trabajador(servicio: ServicioVideo, token: str | None):
    def trabajador(x_video_token: Annotated[str | None, Header()] = None,
                   x_video_nodo: Annotated[str | None, Header(max_length=20)] = None) -> str:
        if not token:
            raise HTTPException(503, "El análisis de video no está activado.")
        if not x_video_token or not hmac.compare_digest(x_video_token, token):
            raise HTTPException(401, "Token del trabajador de video inválido.")
        servicio.latido(x_video_nodo)  # #231: el nodo está vivo y dice su versión
        return x_video_nodo or ""

    return trabajador


async def _guardar(almacen: Almacen, peticion: Request) -> tuple[str, int]:
    try:
        return await almacen.guardar(peticion.stream())
    except ArchivoInvalido as error:
        raise HTTPException(413 if "MB" in str(error) else 415, str(error)) from error


async def _subir_video(servicio: ServicioVideo, almacen: Almacen, token: str | None,
                       codigo: str, peticion: Request, clave: str | None) -> dict:
    if not token:
        raise HTTPException(503, "Por ahora no analizamos videos. Tu reporte ya llegó y "
                                 "se atiende con la descripción.")
    codigo = codigo.upper()
    _ejecutar(servicio.autorizar_subida, codigo, clave)
    if int(peticion.headers.get("content-length") or 0) > MAX_BYTES:
        raise HTTPException(413, "El video pasa de 50 MB.")
    ruta, tamano = await _guardar(almacen, peticion)
    _ejecutar(servicio.registrar, codigo, ruta, tamano)
    return {"estado": "pendiente", "mensaje": "Video recibido, se está analizando."}


async def _subir_vista(servicio: ServicioVideo, almacen_vistas: Almacen, id_: int,
                       peticion: Request) -> dict:
    _ejecutar(servicio.autorizar_vista, id_)
    maximo = config.VISTA_VIDEO_MAX_MB * 1024 * 1024
    if int(peticion.headers.get("content-length") or 0) > maximo:
        raise HTTPException(413, f"La vista pasa de {config.VISTA_VIDEO_MAX_MB} MB.")
    ruta, tamano = await _guardar(almacen_vistas, peticion)
    _ejecutar(servicio.registrar_vista, id_, ruta, tamano)
    return {"bytes": tamano}


def _vista_del_video(servicio: ServicioVideo, almacen_vistas: Almacen, codigo: str):
    vista = servicio.vista_de(codigo.upper())
    if vista is None or not almacen_vistas.existe(vista[0]):
        raise HTTPException(404, "Este reporte no tiene vista previa del video.")
    ruta, tamano = vista
    return StreamingResponse(almacen_vistas.leer(ruta), media_type="video/mp4",
                             headers={"Cache-Control": "private, no-store",
                                      "Content-Length": str(tamano)})


def crear_rutas_video(servicio: ServicioVideo, almacen: Almacen,
                      token: str | None, personal,
                      almacen_vistas: Almacen | None = None
                      ) -> APIRouter:
    rutas = APIRouter()
    _rutas_del_ciudadano_y_del_trabajador(rutas, servicio, almacen, token, almacen_vistas)
    _rutas_del_personal(rutas, servicio, token, personal, almacen_vistas)
    return rutas


def _rutas_del_ciudadano_y_del_trabajador(rutas: APIRouter, servicio: ServicioVideo,
                                          almacen: Almacen, token: str | None,
                                          almacen_vistas: Almacen | None) -> None:
    trabajador = _dependencia_del_trabajador(servicio, token)
    solo_trabajador = [Depends(trabajador)]

    @rutas.post("/reportes/{codigo}/video", status_code=202)
    async def subir_video(codigo: str, peticion: Request,
                          clave: Annotated[str | None, Header(alias="Idempotency-Key")] = None):
        """RF-01 / RF-03: el video (≤ 50 MB) llega después del reporte, sin cuenta."""
        return await _subir_video(servicio, almacen, token, codigo, peticion, clave)

    @rutas.post("/video/trabajos/reclamar", dependencies=solo_trabajador)
    def reclamar_trabajo(nodo: str = Depends(trabajador)):
        trabajo = servicio.reclamar()
        if trabajo is None:
            return Response(status_code=204)
        servicio.latido(nodo or None, ocupado=True)
        return {"id": trabajo.id, "codigo": trabajo.codigo, "bytes": trabajo.bytes}

    @rutas.get("/video/trabajos/{id_}/archivo", dependencies=solo_trabajador)
    def descargar_video(id_: int):
        ruta = _ejecutar(servicio.ruta_para_descargar, id_)
        return StreamingResponse(almacen.leer(ruta), media_type="application/octet-stream")

    @rutas.post("/video/trabajos/{id_}/vista", dependencies=solo_trabajador)
    async def subir_vista(id_: int, peticion: Request):
        """#214: la vista previa liviana (MP4, 5 MB o menos) que ve el veterinario."""
        return await _subir_vista(servicio, almacen_vistas, id_, peticion)

    @rutas.post("/video/trabajos/{id_}/resultado", dependencies=solo_trabajador)
    def entregar_resultado(id_: int, datos: ResultadoEntrada,
                           nodo: str = Depends(trabajador)):
        trabajo = _ejecutar(servicio.terminar, id_, _resultado(datos))
        servicio.latido(nodo or None, ocupado=False)
        return {"estado": trabajo.estado.value, "discrepancia": trabajo.discrepancia}

    @rutas.post("/video/trabajos/{id_}/fallo", dependencies=solo_trabajador)
    def informar_fallo(id_: int, datos: FalloEntrada,
                       nodo: str = Depends(trabajador)):
        estado = _ejecutar(servicio.fallar, id_, datos.motivo).estado.value
        servicio.latido(nodo or None, ocupado=False)
        return {"estado": estado}


def _rutas_del_personal(rutas: APIRouter, servicio: ServicioVideo, token: str | None,
                        personal, almacen_vistas: Almacen | None) -> None:
    @rutas.get("/video/nodo", dependencies=[personal])
    def estado_del_nodo():
        """#231: ¿el equipo que analiza los videos está encendido y con el código al día?"""
        estado = servicio.estado_nodo()
        return {"activado": bool(token), "version_minima": config.VERSION_MINIMA_NODO_VIDEO,
                **estado, "ultimo_contacto": fecha_utc(estado["ultimo_contacto"])}

    @rutas.get("/reportes/{codigo}/video", dependencies=[personal])
    def video_del_reporte(codigo: str):
        trabajo = servicio.de_reporte(codigo.upper())
        if trabajo is None:
            raise HTTPException(404, "Este reporte no tiene video.")
        return vista_para_personal(trabajo)

    @rutas.get("/reportes/{codigo}/video/tira.png", dependencies=[personal])
    def tira_del_video(codigo: str):
        trabajo = servicio.de_reporte(codigo.upper())
        if trabajo is None or trabajo.tira is None:
            raise HTTPException(404, "Este video no tiene tira de cuadros.")
        return Response(trabajo.tira, media_type="image/png",
                        headers={"Cache-Control": "private, no-store"})

    @rutas.get("/reportes/{codigo}/video/vista.mp4", dependencies=[personal])
    def vista_del_video(codigo: str):
        """El personal ve el video con el esqueleto dibujado; nunca el ciudadano (RN-14)."""
        return _vista_del_video(servicio, almacen_vistas, codigo)
