"""Rutas de indicadores, exportaciones y bitácora (RF-30, RF-31, RF-32; DT-13, #267)."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app.api.comun import Contexto, fecha_utc
from app.dominio.modelos import Usuario
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
        reportes_ = repositorio.todos()
        decisiones = {}
        for r in reportes_:
            lista = repositorio.decisiones(r.codigo)
            if lista:
                decisiones[r.codigo] = lista[-1]
        rescates_ = [x for x in (repositorio_rescates.vigente(c) for c in decisiones) if x]
        solicitudes_ = repositorio_adopciones.solicitudes()
        seguimientos_ = [x for s in solicitudes_ for x in repositorio_adopciones.seguimientos(s.id)]
        return Datos(reportes_, decisiones, rescates_, repositorio_refugios.todos(),
                     solicitudes_, seguimientos_, tuple(repositorio_adopciones.perfiles()),
                     tuple(repositorio_adopciones.disponibles()))

    @rutas.get("/indicadores", dependencies=[gestion])
    def indicadores():
        """RF-30: conteos, porcentajes y tiempos; ningún dato personal. Se calculan al pedirlos
        (pocos datos: no hace falta un almacén aparte)."""
        return calcular_indicadores(datos_para_indicadores(), datetime.now(UTC))

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
