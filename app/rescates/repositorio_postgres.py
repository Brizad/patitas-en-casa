"""Rescates en PostgreSQL (HU-06).

RN-08 lo garantizan dos índices únicos parciales: si dos rescatistas aceptan el mismo rescate a
la vez, o una persona acepta dos a la vez, PostgreSQL rechaza el segundo INSERT y aquí se
traduce al error del dominio según el índice que falló.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, RowMapping, insert, select, update
from sqlalchemy.dialects.postgresql import insert as insertar_o_actualizar
from sqlalchemy.exc import IntegrityError

from app.bd.esquema import rescates, rescatistas
from app.dominio.modelos import EstadoRescate, Rescate, ResultadoRescate
from app.rescates.repositorio import ACTIVOS, RescateTomado, RescatistaOcupado

ERRORES_POR_INDICE = {"uq_rescates_reporte_vigente": RescateTomado,
                      "uq_rescates_rescatista_activo": RescatistaOcupado}


class RepositorioRescatesPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def poner_disponible(self, rescatista: str, disponible: bool) -> None:
        sentencia = insertar_o_actualizar(rescatistas).values(correo=rescatista,
                                                              disponible=disponible)
        sentencia = sentencia.on_conflict_do_update(
            index_elements=[rescatistas.c.correo],
            set_={"disponible": disponible, "actualizado_en": sentencia.excluded.actualizado_en})
        with self._motor.begin() as conexion:
            conexion.execute(sentencia)

    def esta_disponible(self, rescatista: str) -> bool:
        with self._motor.connect() as conexion:
            return bool(conexion.execute(select(rescatistas.c.disponible)
                                         .where(rescatistas.c.correo == rescatista)).scalar())

    def aceptar(self, codigo: str, rescatista: str, momento: datetime) -> Rescate:
        try:
            with self._motor.begin() as conexion:
                conexion.execute(insert(rescates).values(
                    reporte_codigo=codigo, rescatista=rescatista,
                    estado=EstadoRescate.EN_CAMINO.value, aceptado_en=momento,
                    actualizado_en=momento))
        except IntegrityError as error:
            indice = getattr(getattr(error.orig, "diag", None), "constraint_name", None)
            if indice in ERRORES_POR_INDICE:
                raise ERRORES_POR_INDICE[indice](codigo) from error
            raise
        return Rescate(codigo=codigo, rescatista=rescatista, estado=EstadoRescate.EN_CAMINO,
                       aceptado_en=momento, actualizado_en=momento)

    def _uno(self, *condiciones) -> Rescate | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(select(rescates).where(*condiciones)).mappings().first()
        return None if fila is None else _a_rescate(fila)

    def vigente(self, codigo: str) -> Rescate | None:
        return self._uno(rescates.c.reporte_codigo == codigo,
                         rescates.c.estado != EstadoRescate.LIBERADO.value)

    def activo_de(self, rescatista: str) -> Rescate | None:
        return self._uno(rescates.c.rescatista == rescatista,
                         rescates.c.estado.in_([e.value for e in ACTIVOS]))

    def codigos_tomados(self) -> set[str]:
        with self._motor.connect() as conexion:
            return set(conexion.execute(
                select(rescates.c.reporte_codigo)
                .where(rescates.c.estado != EstadoRescate.LIBERADO.value)).scalars())

    def avanzar(self, codigo: str, rescatista: str, desde: EstadoRescate,
                hasta: EstadoRescate, momento: datetime,
                resultado: ResultadoRescate | None = None) -> bool:
        with self._motor.begin() as conexion:
            cambio = conexion.execute(
                update(rescates)
                .where(rescates.c.reporte_codigo == codigo,
                       rescates.c.rescatista == rescatista,
                       rescates.c.estado == desde.value)
                .values(estado=hasta.value, actualizado_en=momento,
                        resultado=resultado.value if resultado else None))
        return cambio.rowcount == 1


def _a_rescate(fila: RowMapping) -> Rescate:
    return Rescate(codigo=fila["reporte_codigo"], rescatista=fila["rescatista"],
                   estado=EstadoRescate(fila["estado"]), aceptado_en=fila["aceptado_en"],
                   actualizado_en=fila["actualizado_en"],
                   resultado=ResultadoRescate(fila["resultado"]) if fila["resultado"] else None)
