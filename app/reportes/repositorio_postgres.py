"""Persistencia de reportes en PostgreSQL (DT-01), detrás de RepositorioReportes."""
from __future__ import annotations

from sqlalchemy import Engine, RowMapping, select
from sqlalchemy.dialects.postgresql import insert

from app.bd.esquema import reportes
from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Ubicacion


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


def _a_fila(reporte: Reporte) -> dict:
    return {
        "codigo": reporte.codigo,
        "descripcion": reporte.descripcion,
        "latitud": reporte.ubicacion.latitud,
        "longitud": reporte.ubicacion.longitud,
        "direccion": reporte.ubicacion.direccion,
        "video_segundos": reporte.video_segundos,
        "estado": reporte.estado.value,
        "prioridad": reporte.prioridad.value if reporte.prioridad else None,
        "confianza": reporte.confianza,
        "evidencias": list(reporte.evidencias),
        "creado_en": reporte.creado_en,
    }


def _a_reporte(fila: RowMapping) -> Reporte:
    return Reporte(
        codigo=fila["codigo"],
        descripcion=fila["descripcion"],
        ubicacion=Ubicacion(fila["latitud"], fila["longitud"], fila["direccion"]),
        video_segundos=fila["video_segundos"],
        estado=EstadoReporte(fila["estado"]),
        prioridad=Prioridad(fila["prioridad"]) if fila["prioridad"] else None,
        confianza=fila["confianza"],
        evidencias=list(fila["evidencias"]),
        creado_en=fila["creado_en"],
    )
