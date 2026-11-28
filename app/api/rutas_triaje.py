"""Rutas del triaje: cola, confirmación, descarte, avisos, decisiones e historial del veterinario
(HU-02, RN-06, RN-16, RF-04, RF-17) (DT-13, #267)."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
)
from pydantic import BaseModel, Field

from app import config
from app.api.comun import Contexto, fecha_utc
from app.api.comun import cambiar as _cambio
from app.avisos.repositorio import resumen
from app.dominio.modelos import (
    EstadoReporte,
    MotivoDescarte,
    Prioridad,
    Usuario,
)
from app.reportes import orden
from app.reportes.confirmacion import (
    AjusteSinJustificacion,
    ReporteNoEncontrado,
    ReporteYaConfirmado,
)
from app.reportes.descarte import DescarteInvalido
from app.reportes.duplicados import posibles_duplicados
from app.rescates.servicio import (
    PRIORIDADES_DE_RESCATE,
)
from app.triaje.servicio import ordenar_cola


class ConfirmacionEntrada(BaseModel):
    """Sin prioridad se confirma la sugerida; con otra distinta, la justificación es
    obligatoria (RN-16)."""

    prioridad: Prioridad | None = None
    justificacion: str | None = Field(default=None, max_length=1000)


class DescarteEntrada(BaseModel):
    """D-02: falso o duplicado (con el código del original, opcional)."""

    motivo: MotivoDescarte
    justificacion: str | None = Field(default=None, max_length=1000)
    duplicado_de: str | None = Field(default=None, max_length=8)


def _cola(ctx: Contexto) -> list[dict]:
    pendientes = ctx.repositorio.pendientes()  # A-03 (#239): no toda la historia
    # RF-17: un duplicado está a 2 horas o menos; basta con lo creado desde entonces.
    todos = ctx.repositorio.creados_desde(
        min(r.creado_en for r in pendientes) - timedelta(hours=config.DUPLICADO_HORAS)
    ) if pendientes else []
    ahora = datetime.now(UTC)
    fotos = ctx.repositorio_rescates.fotos_de_reportes([r.codigo for r in pendientes])  # #504
    return [
        {"codigo": r.codigo, "prioridad": r.prioridad.value, "estado": r.estado.value,
         # #496: nivel, atrasado (más de 72 h sin avanzar) y lo que dice el propio reporte.
         "nivel": orden.nivel(r.prioridad), "atrasado": orden.atrasado(r.creado_en, ahora),
         "especie": orden.especie_mencionada(r.descripcion),
         "estado_animal": orden.estado_del_animal(r.evidencias, r.descripcion),
         "confianza": r.confianza, "evidencias": r.evidencias,
         "version_modelo": r.version_modelo,
         # Detalle para decidir de un vistazo: qué pasó, dónde y cuándo. Nunca el contacto.
         "descripcion": r.descripcion, "creado_en": fecha_utc(r.creado_en),
         "video_segundos": r.video_segundos,
         "foto": f"/fotos/{fotos[r.codigo]}" if r.codigo in fotos else None,
         "ubicacion": {"latitud": r.ubicacion.latitud, "longitud": r.ubicacion.longitud,
                       "direccion": r.ubicacion.direccion, "comuna": r.ubicacion.comuna},
         # RF-17: se compara también con los ya confirmados (el original suele estarlo).
         "posibles_duplicados": posibles_duplicados(r, todos)}
        for r in ordenar_cola(pendientes)
    ]


def _confirmar(ctx: Contexto, codigo: str, datos: ConfirmacionEntrada, peticion: Request,
               veterinario: Usuario) -> dict:
    try:
        resultado = ctx.confirmaciones.confirmar_y_programar(
            codigo.upper(), veterinario, datos.prioridad, datos.justificacion)
    except ReporteNoEncontrado as error:
        raise HTTPException(status_code=404, detail="Reporte no encontrado.") from error
    except ReporteYaConfirmado as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except AjusteSinJustificacion as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    decision = resultado.decision
    _cambio(peticion, {"prioridad": decision.prioridad_sugerida.value},
            {"prioridad": decision.prioridad_final.value,
             "estado": EstadoReporte.CONFIRMADO.value})
    if decision.prioridad_final not in PRIORIDADES_DE_RESCATE:
        estado_aviso = "no_aplica"  # media y baja las programa el refugio
    else:
        estado_aviso = "pendiente" if resultado.avisos else "sin_destinatarios"
    return {"codigo": decision.codigo, "estado": EstadoReporte.CONFIRMADO.value,
            "prioridad": decision.prioridad_final.value, "ajustada": decision.ajustada,
            "avisos": {"programados": resultado.avisos, "estado": estado_aviso}}


def _descartar(ctx: Contexto, codigo: str, datos: DescarteEntrada, peticion: Request,
               veterinario: Usuario) -> dict:
    antes = ctx.repositorio.buscar(codigo.upper())
    original = datos.duplicado_de.upper() if datos.duplicado_de else None
    try:
        ctx.descartes.descartar(codigo.upper(), veterinario, datos.motivo, datos.justificacion,
                                duplicado_de=original)
    except ReporteNoEncontrado as error:
        raise HTTPException(status_code=404, detail="Reporte no encontrado.") from error
    except ReporteYaConfirmado as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DescarteInvalido as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    _cambio(peticion, {"estado": antes.estado.value},
            {"estado": EstadoReporte.DESCARTADO.value, "motivo": datos.motivo.value})
    return {"codigo": codigo.upper(), "estado": EstadoReporte.DESCARTADO.value}


def _avisos(ctx: Contexto, codigo: str) -> dict:
    codigo = codigo.upper()
    avisos = ctx.repositorio_avisos.de_reporte(codigo)
    return {"codigo": codigo, "resumen": resumen(avisos),
            "avisos": [{"destinatario": a.destinatario, "estado": a.estado.value,
                        "intentos": a.intentos, "ultimo_error": a.ultimo_error}
                       for a in avisos]}


def _historial(ctx: Contexto, veterinario: Usuario) -> list[dict]:
    repositorio = ctx.repositorio
    decisiones = repositorio.decisiones_de(veterinario.correo)
    descartes = repositorio.descartes_de(veterinario.correo)
    # DT-12 (#265): todos los reportes en una consulta, no uno por fila.
    reportes_ = repositorio.buscar_varios([x.codigo for x in [*decisiones, *descartes]])
    filas = []
    for d in decisiones:
        ajustada = d.prioridad_final != d.prioridad_sugerida
        filas.append((d.decidido_en, {
            "codigo": d.codigo, "accion": "ajustado" if ajustada else "confirmado",
            "prioridad_sugerida": d.prioridad_sugerida.value,
            "prioridad_final": d.prioridad_final.value, "justificacion": d.justificacion}))
    for x in descartes:
        reporte = reportes_.get(x.codigo)
        sugerida = reporte.prioridad if reporte else None
        filas.append((x.descartado_en, {
            "codigo": x.codigo,
            "accion": "archivado" if x.motivo == MotivoDescarte.ARCHIVADO else "descartado",
            "prioridad_sugerida": sugerida.value if sugerida else None,
            "prioridad_final": None, "justificacion": x.justificacion}))
    resultado = []
    for fecha, fila in sorted(filas, key=lambda f: f[0], reverse=True):
        reporte = reportes_.get(fila["codigo"])
        resultado.append({**fila, "fecha": fecha_utc(fecha),
                          "estado": reporte.estado.value if reporte else None})
    return resultado


def crear_rutas_triaje(ctx: Contexto) -> APIRouter:
    rutas = APIRouter()
    _rutas_de_cola_y_confirmacion(rutas, ctx)
    _rutas_de_descarte_y_consultas(rutas, ctx)
    return rutas


def _rutas_de_cola_y_confirmacion(rutas: APIRouter, ctx: Contexto) -> None:
    personal = ctx.personal
    veterinaria = ctx.veterinaria

    @rutas.get("/cola", dependencies=[personal])
    def cola():
        """Reportes pendientes de confirmar (HU-02); los confirmados salen de la cola."""
        return _cola(ctx)

    @rutas.post("/reportes/{codigo}/confirmacion")
    def confirmar_prioridad(codigo: str, datos: ConfirmacionEntrada, peticion: Request,
                            veterinario: Usuario = veterinaria):
        """HU-02: el veterinario confirma la prioridad sugerida o la ajusta con justificación.

        #63 (outbox): si queda crítica o alta, los avisos a los rescatistas de la zona se
        guardan como pendientes en la misma transacción y el procesador los envía después.
        La respuesta dice que el aviso está pendiente, nunca que llegó (D-05)."""
        return _confirmar(ctx, codigo, datos, peticion, veterinario)


def _rutas_de_descarte_y_consultas(rutas: APIRouter, ctx: Contexto) -> None:
    personal = ctx.personal
    veterinaria = ctx.veterinaria

    @rutas.post("/reportes/{codigo}/descarte")
    def descartar_reporte(codigo: str, datos: DescarteEntrada, peticion: Request,
                          veterinario: Usuario = veterinaria):
        """D-02: falso o duplicado. Como confirmar, sale de la cola y es una sola vez (409)."""
        return _descartar(ctx, codigo, datos, peticion, veterinario)

    @rutas.get("/reportes/{codigo}/avisos", dependencies=[personal])
    def avisos_del_reporte(codigo: str):
        """#63: estado real de los avisos de un reporte (pendiente, enviado, fallido…)."""
        return _avisos(ctx, codigo)

    @rutas.get("/reportes/{codigo}/decisiones", dependencies=[personal])
    def bitacora_de_triaje(codigo: str):
        return [{"veterinario": d.veterinario, "prioridad_sugerida": d.prioridad_sugerida.value,
                 "prioridad_final": d.prioridad_final.value, "justificacion": d.justificacion,
                 "decidido_en": fecha_utc(d.decidido_en), "version_modelo": d.version_modelo}
                for d in ctx.repositorio.decisiones(codigo.upper())]

    @rutas.get("/veterinario/historial")
    def historial_del_veterinario(veterinario: Usuario = veterinaria):
        """Lo que este veterinario confirmó, ajustó o descartó, del más reciente al más viejo.
        Sale de la bitácora `decisiones_triaje` y de los descartes (D-02)."""
        return _historial(ctx, veterinario)
