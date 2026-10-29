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
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.dominio.modelos import Prioridad
from app.video.almacen import MAX_BYTES, AlmacenEnDisco, ArchivoInvalido
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
            "version_modelo": t.version_modelo, "tiene_tira": t.tira is not None}


# C901: como en crear_app, mccabe suma las rutas anidadas; cada una por separado es sencilla.
def crear_rutas_video(servicio: ServicioVideo, almacen: AlmacenEnDisco,  # noqa: C901
                      token: str | None, personal) -> APIRouter:
    rutas = APIRouter()

    def _ejecutar(funcion, *argumentos):
        try:
            return funcion(*argumentos)
        except VideoRechazado as error:
            raise HTTPException(error.estado_http, str(error)) from error

    def trabajador(x_video_token: Annotated[str | None, Header()] = None) -> None:
        if not token:
            raise HTTPException(503, "El análisis de video no está activado.")
        if not x_video_token or not hmac.compare_digest(x_video_token, token):
            raise HTTPException(401, "Token del trabajador de video inválido.")

    solo_trabajador = [Depends(trabajador)]

    @rutas.post("/reportes/{codigo}/video", status_code=202)
    async def subir_video(codigo: str, peticion: Request,
                          clave: Annotated[str | None, Header(alias="Idempotency-Key")] = None):
        """RF-01 / RF-03: el video (≤ 50 MB) llega después del reporte, sin cuenta."""
        if not token:
            raise HTTPException(503, "Por ahora no analizamos videos. Tu reporte ya llegó y "
                                     "se atiende con la descripción.")
        codigo = codigo.upper()
        _ejecutar(servicio.autorizar_subida, codigo, clave)
        if int(peticion.headers.get("content-length") or 0) > MAX_BYTES:
            raise HTTPException(413, "El video pasa de 50 MB.")
        try:
            ruta, tamano = await almacen.guardar(peticion.stream())
        except ArchivoInvalido as error:
            raise HTTPException(413 if "MB" in str(error) else 415, str(error)) from error
        _ejecutar(servicio.registrar, codigo, ruta, tamano)
        return {"estado": "pendiente", "mensaje": "Video recibido, se está analizando."}

    @rutas.post("/video/trabajos/reclamar", dependencies=solo_trabajador)
    def reclamar_trabajo():
        trabajo = servicio.reclamar()
        if trabajo is None:
            return Response(status_code=204)
        return {"id": trabajo.id, "codigo": trabajo.codigo, "bytes": trabajo.bytes}

    @rutas.get("/video/trabajos/{id_}/archivo", dependencies=solo_trabajador)
    def descargar_video(id_: int):
        return FileResponse(_ejecutar(servicio.ruta_para_descargar, id_),
                            media_type="application/octet-stream")

    @rutas.post("/video/trabajos/{id_}/resultado", dependencies=solo_trabajador)
    def entregar_resultado(id_: int, datos: ResultadoEntrada):
        trabajo = _ejecutar(servicio.terminar, id_, _resultado(datos))
        return {"estado": trabajo.estado.value, "discrepancia": trabajo.discrepancia}

    @rutas.post("/video/trabajos/{id_}/fallo", dependencies=solo_trabajador)
    def informar_fallo(id_: int, datos: FalloEntrada):
        return {"estado": _ejecutar(servicio.fallar, id_, datos.motivo).estado.value}

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

    return rutas
