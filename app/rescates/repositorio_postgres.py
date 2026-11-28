"""Rescates en PostgreSQL (HU-06).

RN-08 lo garantizan dos índices únicos parciales: si dos rescatistas aceptan el mismo rescate a
la vez, o una persona acepta dos a la vez, PostgreSQL rechaza el segundo INSERT y aquí se
traduce al error del dominio según el índice que falló.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, RowMapping, delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as insertar_o_actualizar
from sqlalchemy.exc import IntegrityError

from app.bd.esquema import (
    escalamientos,
    fotos_evidencia,
    informes_rescate,
    rescates,
    rescatistas,
    ubicaciones_rescate,
)
from app.dominio.modelos import (
    Encontrado,
    EstadoAnimal,
    EstadoRescate,
    FotoEvidencia,
    InformeRescate,
    Rescate,
    ResultadoRescate,
    UbicacionRescatista,
)
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

    def poner_zona(self, rescatista: str, comunas: frozenset[int]) -> None:
        sentencia = insertar_o_actualizar(rescatistas).values(correo=rescatista,
                                                              comunas=sorted(comunas))
        sentencia = sentencia.on_conflict_do_update(
            index_elements=[rescatistas.c.correo],
            set_={"comunas": sentencia.excluded.comunas,
                  "actualizado_en": sentencia.excluded.actualizado_en})
        with self._motor.begin() as conexion:
            conexion.execute(sentencia)

    def zona(self, rescatista: str) -> frozenset[int]:
        with self._motor.connect() as conexion:
            comunas = conexion.execute(select(rescatistas.c.comunas)
                                       .where(rescatistas.c.correo == rescatista)).scalar()
        return frozenset(comunas or ())

    def disponibles(self) -> dict[str, frozenset[int]]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(rescatistas.c.correo, rescatistas.c.comunas)
                                     .where(rescatistas.c.disponible))
            return {correo: frozenset(comunas) for correo, comunas in filas}

    def marcar_escalado(self, codigo: str, momento: datetime) -> bool:
        """INSERT ... ON CONFLICT DO NOTHING: si dos procesos escalan a la vez, solo uno
        inserta la fila y solo ese avisa (RETURNING trae la fila solo si se insertó)."""
        sentencia = (insertar_o_actualizar(escalamientos)
                     .values(reporte_codigo=codigo, escalado_en=momento)
                     .on_conflict_do_nothing(index_elements=[escalamientos.c.reporte_codigo])
                     .returning(escalamientos.c.reporte_codigo))
        with self._motor.begin() as conexion:
            return conexion.execute(sentencia).scalar() is not None

    def escalados(self) -> set[str]:
        with self._motor.connect() as conexion:
            return set(conexion.execute(select(escalamientos.c.reporte_codigo)).scalars())

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

    def vigentes(self) -> list[Rescate]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(rescates).where(
                rescates.c.estado != EstadoRescate.LIBERADO.value)).mappings().all()
        return [_a_rescate(f) for f in filas]

    def activo_de(self, rescatista: str) -> Rescate | None:
        return self._uno(rescates.c.rescatista == rescatista,
                         rescates.c.estado.in_([e.value for e in ACTIVOS]))

    def historial_de(self, rescatista: str) -> list[Rescate]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(
                select(rescates).where(rescates.c.rescatista == rescatista,
                                       rescates.c.estado != EstadoRescate.LIBERADO.value)
                .order_by(rescates.c.aceptado_en.desc())).mappings()
            return [_a_rescate(f) for f in filas]

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
                        resultado=resultado.value if resultado else None,
                        **({"llegada_en": momento} if hasta == EstadoRescate.EN_SITIO else {})))
            if cambio.rowcount == 1 and hasta != EstadoRescate.EN_CAMINO:
                # #498: fuera de «en camino» no queda ninguna posición guardada.
                conexion.execute(delete(ubicaciones_rescate)
                                 .where(ubicaciones_rescate.c.reporte_codigo == codigo))
        return cambio.rowcount == 1

    def guardar_ubicacion(self, ubicacion: UbicacionRescatista, rescatista: str) -> bool:
        """En una transacción: bloquea la fila del rescate (FOR UPDATE) y solo si es suyo y va en
        camino reemplaza la última posición. Un «avanzar» a la vez espera a que esto termine y
        luego borra la posición; si avanzó antes, aquí ya no encuentra el rescate en camino."""
        u = ubicaciones_rescate.c
        datos = {"latitud": ubicacion.latitud, "longitud": ubicacion.longitud,
                 "simulada": ubicacion.simulada, "actualizada_en": ubicacion.actualizada_en}
        sentencia = insertar_o_actualizar(ubicaciones_rescate).values(
            reporte_codigo=ubicacion.codigo, **datos)
        sentencia = sentencia.on_conflict_do_update(index_elements=[u.reporte_codigo], set_=datos)
        with self._motor.begin() as conexion:
            suyo = conexion.execute(
                select(rescates.c.id).where(rescates.c.reporte_codigo == ubicacion.codigo,
                                            rescates.c.rescatista == rescatista,
                                            rescates.c.estado == EstadoRescate.EN_CAMINO.value)
                .with_for_update()).first()
            if suyo is None:
                return False
            conexion.execute(sentencia)
        return True

    def ubicacion(self, codigo: str) -> UbicacionRescatista | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(select(ubicaciones_rescate).where(
                ubicaciones_rescate.c.reporte_codigo == codigo)).mappings().first()
        if fila is None:
            return None
        return UbicacionRescatista(fila["reporte_codigo"], fila["latitud"], fila["longitud"],
                                   fila["actualizada_en"], fila["simulada"])

    def borrar_ubicacion(self, codigo: str) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(delete(ubicaciones_rescate)
                             .where(ubicaciones_rescate.c.reporte_codigo == codigo))


    # --- #504: informe del rescate y fotos de evidencia ---------------------------------------

    def atender_con_informe(self, informe: InformeRescate,
                            fotos: list[tuple[str, bytes]]) -> bool:
        with self._motor.begin() as conexion:
            cambio = conexion.execute(
                update(rescates)
                .where(rescates.c.reporte_codigo == informe.codigo,
                       rescates.c.rescatista == informe.rescatista,
                       rescates.c.estado == EstadoRescate.EN_SITIO.value)
                .values(estado=EstadoRescate.ATENDIDO.value, resultado=informe.resultado.value,
                        actualizado_en=informe.creado_en))
            if cambio.rowcount != 1:
                return False
            conexion.execute(insert(informes_rescate).values(
                reporte_codigo=informe.codigo, rescatista=informe.rescatista,
                encontrado=informe.encontrado.value, estados=[e.value for e in informe.estados],
                resultado=informe.resultado.value, motivo=informe.motivo, nota=informe.nota,
                creado_en=informe.creado_en))
            for tipo, datos in fotos:
                conexion.execute(insert(fotos_evidencia).values(
                    reporte_codigo=informe.codigo, origen="rescate", tipo=tipo, datos=datos,
                    creada_en=informe.creado_en))
        return True

    def informe(self, codigo: str) -> InformeRescate | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(select(informes_rescate).where(
                informes_rescate.c.reporte_codigo == codigo)).mappings().first()
        return _a_informe(fila) if fila else None

    def informes_recientes(self, limite: int) -> list[InformeRescate]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(informes_rescate)
                                     .order_by(informes_rescate.c.creado_en.desc())
                                     .limit(limite)).mappings().all()
        return [_a_informe(f) for f in filas]

    def guardar_foto_reporte(self, codigo: str, tipo: str, datos: bytes,
                             momento: datetime) -> int | None:
        sentencia = insertar_o_actualizar(fotos_evidencia).values(
            reporte_codigo=codigo, origen="reporte", tipo=tipo, datos=datos, creada_en=momento
        ).on_conflict_do_nothing(index_elements=[fotos_evidencia.c.reporte_codigo],
                                 index_where=fotos_evidencia.c.origen == "reporte"
                                 ).returning(fotos_evidencia.c.id)
        with self._motor.begin() as conexion:
            return conexion.execute(sentencia).scalar()

    def fotos_de(self, codigo: str) -> list[FotoEvidencia]:
        f = fotos_evidencia.c
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(f.id, f.reporte_codigo, f.origen, f.tipo, f.creada_en)
                                     .where(f.reporte_codigo == codigo)
                                     .order_by(f.id)).mappings().all()
        return [_a_foto(fila) for fila in filas]

    def foto(self, foto_id: int) -> tuple[FotoEvidencia, bytes] | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(select(fotos_evidencia).where(
                fotos_evidencia.c.id == foto_id)).mappings().first()
        return (_a_foto(fila), bytes(fila["datos"])) if fila else None

    def fotos_de_reportes(self, codigos: list[str]) -> dict[str, int]:
        if not codigos:
            return {}
        f = fotos_evidencia.c
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(f.reporte_codigo, f.id).where(
                f.reporte_codigo.in_(codigos), f.origen == "reporte")).all()
        return {codigo: foto_id for codigo, foto_id in filas}


def _a_informe(fila: RowMapping) -> InformeRescate:
    return InformeRescate(
        codigo=fila["reporte_codigo"], rescatista=fila["rescatista"],
        encontrado=Encontrado(fila["encontrado"]),
        estados=tuple(EstadoAnimal(e) for e in fila["estados"]),
        resultado=ResultadoRescate(fila["resultado"]), motivo=fila["motivo"], nota=fila["nota"],
        creado_en=fila["creado_en"])


def _a_foto(fila: RowMapping) -> FotoEvidencia:
    return FotoEvidencia(fila["id"], fila["reporte_codigo"], fila["origen"], fila["tipo"],
                         fila["creada_en"])


def _a_rescate(fila: RowMapping) -> Rescate:
    return Rescate(codigo=fila["reporte_codigo"], rescatista=fila["rescatista"],
                   estado=EstadoRescate(fila["estado"]), aceptado_en=fila["aceptado_en"],
                   actualizado_en=fila["actualizado_en"], llegada_en=fila["llegada_en"],
                   resultado=ResultadoRescate(fila["resultado"]) if fila["resultado"] else None)
