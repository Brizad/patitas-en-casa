"""Persistencia de reportes en PostgreSQL (DT-01), detrás de RepositorioReportes."""
from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import Engine, RowMapping, select, update
from sqlalchemy import insert as insertar
from sqlalchemy.dialects.postgresql import insert

from app.avisos.modelos import AvisoNuevo
from app.avisos.repositorio_postgres import insertar_avisos
from app.bd.esquema import decisiones_triaje, reportes
from app.dominio.modelos import DecisionTriaje, EstadoReporte, Prioridad, Reporte, Ubicacion


class RepositorioPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def guardar(self, reporte: Reporte) -> None:
        """Inserta el reporte o, si el código ya existe, lo actualiza (upsert)."""
        fila = _a_fila(reporte)
        sentencia = insert(reportes).values(**fila)
        sentencia = sentencia.on_conflict_do_update(
            index_elements=[reportes.c.codigo],
            set_={columna: sentencia.excluded[columna] for columna in fila if columna != "codigo"},
        )
        with self._motor.begin() as conexion:
            conexion.execute(sentencia)

    def buscar(self, codigo: str) -> Reporte | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(
                select(reportes).where(reportes.c.codigo == codigo)
            ).mappings().first()
        return None if fila is None else _a_reporte(fila)

    def todos(self) -> list[Reporte]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(reportes).order_by(reportes.c.creado_en)).mappings()
            return [_a_reporte(fila) for fila in filas]

    def guardar_con_clave(self, reporte: Reporte, clave: str) -> Reporte:
        """ON CONFLICT DO NOTHING sobre la columna única: si dos reenvíos llegan a la vez,
        PostgreSQL hace esperar al segundo, que no inserta y lee el reporte del primero."""
        sentencia = (insert(reportes).values(**_a_fila(reporte), clave_idempotencia=clave)
                     .on_conflict_do_nothing(index_elements=[reportes.c.clave_idempotencia])
                     .returning(reportes.c.codigo))
        with self._motor.begin() as conexion:
            if conexion.execute(sentencia).first() is not None:
                return reporte
            fila = conexion.execute(
                select(reportes).where(reportes.c.clave_idempotencia == clave)
            ).mappings().one()
        return _a_reporte(fila)

    def buscar_por_clave(self, clave: str) -> Reporte | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(
                select(reportes).where(reportes.c.clave_idempotencia == clave)
            ).mappings().first()
        return None if fila is None else _a_reporte(fila)

    def confirmar(self, decision: DecisionTriaje, avisos: Sequence[AvisoNuevo] = ()) -> bool:
        """UPDATE condicional: si dos veterinarios confirman a la vez, PostgreSQL bloquea la
        fila y el segundo ya no cumple "estado <> confirmado" (mismo patrón que DT-05).
        #63: los avisos se insertan en la misma transacción; si algo falla, nada queda."""
        with self._motor.begin() as conexion:
            cambio = conexion.execute(
                update(reportes)
                .where(reportes.c.codigo == decision.codigo,
                       reportes.c.estado != EstadoReporte.CONFIRMADO.value)
                .values(estado=EstadoReporte.CONFIRMADO.value,
                        prioridad=decision.prioridad_final.value)
            )
            if cambio.rowcount == 0:
                return False
            conexion.execute(insertar(decisiones_triaje).values(
                reporte_codigo=decision.codigo, veterinario=decision.veterinario,
                prioridad_sugerida=decision.prioridad_sugerida.value,
                prioridad_final=decision.prioridad_final.value,
                justificacion=decision.justificacion, decidido_en=decision.decidido_en,
                version_modelo=decision.version_modelo,
            ))
            insertar_avisos(conexion, decision.codigo, avisos, decision.decidido_en)
        return True

    def decisiones(self, codigo: str) -> list[DecisionTriaje]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(
                select(decisiones_triaje).where(decisiones_triaje.c.reporte_codigo == codigo)
                .order_by(decisiones_triaje.c.decidido_en)
            ).mappings()
            return [DecisionTriaje(
                codigo=f["reporte_codigo"], veterinario=f["veterinario"],
                prioridad_sugerida=Prioridad(f["prioridad_sugerida"]),
                prioridad_final=Prioridad(f["prioridad_final"]),
                justificacion=f["justificacion"], decidido_en=f["decidido_en"],
                version_modelo=f["version_modelo"],
            ) for f in filas]


def _a_fila(reporte: Reporte) -> dict:
    return {
        "codigo": reporte.codigo,
        "descripcion": reporte.descripcion,
        "latitud": reporte.ubicacion.latitud,
        "longitud": reporte.ubicacion.longitud,
        "direccion": reporte.ubicacion.direccion,
        "comuna": reporte.ubicacion.comuna,
        "video_segundos": reporte.video_segundos,
        "estado": reporte.estado.value,
        "prioridad": reporte.prioridad.value if reporte.prioridad else None,
        "confianza": reporte.confianza,
        "evidencias": list(reporte.evidencias),
        "creado_en": reporte.creado_en,
        "version_modelo": reporte.version_modelo,
    }


def _a_reporte(fila: RowMapping) -> Reporte:
    return Reporte(
        codigo=fila["codigo"],
        descripcion=fila["descripcion"],
        ubicacion=Ubicacion(fila["latitud"], fila["longitud"], fila["direccion"],
                            fila["comuna"]),
        video_segundos=fila["video_segundos"],
        estado=EstadoReporte(fila["estado"]),
        prioridad=Prioridad(fila["prioridad"]) if fila["prioridad"] else None,
        confianza=fila["confianza"],
        evidencias=list(fila["evidencias"]),
        creado_en=fila["creado_en"],
        version_modelo=fila["version_modelo"],
    )
