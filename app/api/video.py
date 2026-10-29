"""Rutas del video del reporte (#125, RF-03, RF-19, RNF-02).

- El ciudadano sube el video con la misma clave con la que creó el reporte (sin cuenta).
- Sin PATITAS_VIDEO_TOKEN configurado, el análisis de video está apagado y todo funciona como
  antes (manda el texto). Las rutas del trabajador local llegan en el siguiente cambio.
- El personal ve el resultado y la tira de cuadros; el ciudadano nunca (RN-14).
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, Response

from app.video.almacen import MAX_BYTES, AlmacenEnDisco, ArchivoInvalido
from app.video.modelos import TrabajoVideo
from app.video.servicio import ServicioVideo, VideoRechazado


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
