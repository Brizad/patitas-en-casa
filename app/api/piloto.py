"""Rutas del piloto de usabilidad (RNF-06, #258).

- El administrador invita participantes y descarga los resultados (CSV de resultados_piloto.py).
- La PWA, en modo piloto, manda el reporte de prueba y el SUS con el encabezado `X-Piloto`
  (token de un solo uso). El reporte se valida como uno real y **no se guarda**: nunca llega a
  la cola ni a los rescatistas.
"""
# Sin «from __future__ import annotations»: el modelo del reporte llega como variable y FastAPI
# necesita la clase real para leerlo del cuerpo.
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.dominio.modelos import Ubicacion
from app.piloto.servicio import PREGUNTAS_SUS, PilotoRechazado, ServicioPiloto, puntaje_sus
from app.reportes.servicio import ReporteInvalido

Token = Annotated[str | None, Header(alias="X-Piloto", max_length=64)]


class RespuestasSus(BaseModel):
    segundos: int = Field(ge=1, le=3600)
    respuestas: list[int] = Field(min_length=PREGUNTAS_SUS, max_length=PREGUNTAS_SUS)


def crear_rutas_piloto(servicio: ServicioPiloto, administracion, modelo_reporte) -> APIRouter:
    rutas = APIRouter()

    def _ejecutar(funcion, *argumentos):
        try:
            return funcion(*argumentos)
        except PilotoRechazado as error:
            raise HTTPException(error.estado_http, str(error)) from error
        except ReporteInvalido as error:
            raise HTTPException(422, str(error)) from error

    @rutas.post("/admin/piloto/participantes", status_code=201)
    def invitar_participante(_admin=administracion):
        """RNF-06: un participante anónimo nuevo y el enlace de la PWA en modo prueba."""
        participante, token = servicio.invitar()
        return {"participante": participante.codigo, "token": token,
                "enlace": f"/app/?piloto={token}#reportar",
                "vence_en": participante.vence_en.isoformat()}

    @rutas.get("/admin/piloto/resultados")
    def resultados_del_piloto(_admin=administracion):
        completos = servicio.completos()
        return {"invitados": servicio.invitados(), "completos": len(completos),
                "filas": [{"participante": p.codigo, "segundos": p.segundos,
                           "sus": puntaje_sus(p.sus)} for p in completos]}

    @rutas.get("/admin/piloto/resultados.csv")
    def descargar_resultados(_admin=administracion):
        return Response(servicio.csv(), media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": 'attachment; filename="resultados_piloto.csv"'})

    @rutas.post("/piloto/reportes", status_code=201)
    def reporte_de_prueba(datos: modelo_reporte, token: Token = None):
        """Como POST /reportes, pero no guarda nada en reportes (no va a la cola)."""
        ubicacion = Ubicacion(datos.latitud, datos.longitud, datos.direccion, datos.comuna)
        codigo = _ejecutar(servicio.reportar, token, datos.descripcion, ubicacion,
                           datos.video_segundos, datos.video_mb)
        return {"codigo": codigo, "estado": "piloto"}

    @rutas.post("/piloto/resultados", status_code=201)
    def responder_sus(datos: RespuestasSus, token: Token = None):
        p = _ejecutar(servicio.responder, token, datos.segundos, datos.respuestas)
        return {"participante": p.codigo}

    return rutas
