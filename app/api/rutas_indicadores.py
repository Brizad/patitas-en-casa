"""Rutas de indicadores, exportaciones y bitácora (RF-30, RF-31, RF-32; DT-13, #267)."""
from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app import config
from app.adopciones.modelos import EstadoSolicitud
from app.api.comun import Contexto, fecha_utc
from app.dominio.modelos import ResultadoRescate, Usuario
from app.indicadores.calculo import Datos
from app.indicadores.calculo import calcular as calcular_indicadores
from app.indicadores.exportar import a_csv, fichas_csv, filas_anonimizadas, resumen_pdf


def crear_rutas_indicadores(ctx: Contexto) -> APIRouter:
    rutas = APIRouter()
    repositorio, repositorio_rescates = ctx.repositorio, ctx.repositorio_rescates
    repositorio_adopciones = ctx.repositorio_adopciones
    repositorio_refugios = ctx.repositorio_refugios
    repositorio_bitacora, fichas_de = ctx.repositorio_bitacora, ctx.fichas_de
    gestion, administracion = ctx.gestion, ctx.administracion

    def datos_para_indicadores() -> Datos:
        """Un número fijo de consultas, haya 10 reportes o 10 000 (antes: una por reporte,
        una por decisión y una por solicitud). El resultado y su orden son los mismos."""
        reportes_ = repositorio.todos()
        ultimas = repositorio.ultimas_decisiones()
        decisiones = {r.codigo: ultimas[r.codigo] for r in reportes_ if r.codigo in ultimas}
        vigentes = {x.codigo: x for x in repositorio_rescates.vigentes()}
        rescates_ = [vigentes[c] for c in decisiones if c in vigentes]
        solicitudes_ = repositorio_adopciones.solicitudes()
        por_solicitud: dict[int, list] = {}
        for x in repositorio_adopciones.todos_los_seguimientos():
            por_solicitud.setdefault(x.solicitud_id, []).append(x)
        seguimientos_ = [x for s in solicitudes_ for x in por_solicitud.get(s.id, [])]
        return Datos(reportes_, decisiones, rescates_, repositorio_refugios.todos(),
                     solicitudes_, seguimientos_, tuple(repositorio_adopciones.perfiles()),
                     tuple(repositorio_adopciones.disponibles()))

    @rutas.get("/indicadores", dependencies=[gestion])
    def indicadores():
        """RF-30: conteos, porcentajes y tiempos; ningún dato personal. Se calculan al pedirlos
        (pocos datos: no hace falta un almacén aparte)."""
        return calcular_indicadores(datos_para_indicadores(), datetime.now(UTC))

    publicas: dict = {"hasta": 0.0, "cifras": None}

    @rutas.get("/indicadores/publicos")
    def indicadores_publicos():
        """#426, público (página de inicio): solo tres totales anónimos, sin nada por persona,
        zona ni fecha. Se recalculan cada CACHE_INDICADORES_PUBLICOS_S como mucho: las visitas a
        la portada no despiertan la base a cada rato."""
        if publicas["cifras"] is None or time.monotonic() >= publicas["hasta"]:
            d = datos_para_indicadores()
            publicas["cifras"] = {
                "reportes": len(d.reportes),
                "rescatados": sum(r.resultado in (ResultadoRescate.TRASLADADO,
                                                  ResultadoRescate.ATENDIDO_EN_SITIO)
                                  for r in d.rescates),
                "adoptados": sum(s.estado == EstadoSolicitud.APROBADA for s in d.solicitudes)}
            publicas["hasta"] = time.monotonic() + config.CACHE_INDICADORES_PUBLICOS_S
        return publicas["cifras"]

    @rutas.get("/indicadores/reportes.csv", dependencies=[gestion])
    def exportar_reportes_csv():
        """RF-31: una fila por reporte, sin descripción, dirección, GPS, hora ni código."""
        d = datos_para_indicadores()
        return Response(a_csv(filas_anonimizadas(d.reportes, d.decisiones)),
                        media_type="text/csv; charset=utf-8", headers={
                            "Content-Disposition": 'attachment; filename="reportes.csv"'})

    @rutas.get("/indicadores/fichas.csv")
    def exportar_fichas_csv(usuario: Usuario = gestion):
        """RF-31: fichas del refugio de la persona, sin el texto de las notas clínicas."""
        repo = fichas_de(usuario)
        filas = [(a, len(repo.historial(a.id))) for a in repo.animales()]
        return Response(fichas_csv(filas), media_type="text/csv; charset=utf-8", headers={
            "Content-Disposition": 'attachment; filename="fichas.csv"'})

    @rutas.get("/indicadores/resumen.pdf", dependencies=[gestion])
    def exportar_resumen_pdf():
        ahora = datetime.now(UTC)
        pdf = resumen_pdf(calcular_indicadores(datos_para_indicadores(), ahora),
                          ahora.strftime("%Y-%m-%d %H:%M"))
        return Response(pdf, media_type="application/pdf", headers={
            "Content-Disposition": 'attachment; filename="indicadores.pdf"'})

    @rutas.get("/bitacora")
    def ver_bitacora(limite: int = 100, _admin: Usuario = administracion):
        return [{"momento": fecha_utc(e.momento), "actor": e.actor, "accion": e.accion,
                 "objeto": e.objeto, "estado_http": e.estado_http,
                 "valor_anterior": e.anterior, "valor_nuevo": e.nuevo}
                for e in repositorio_bitacora.recientes(min(max(limite, 1), 500))]

    return rutas
