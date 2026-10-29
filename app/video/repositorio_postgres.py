"""RepositorioVideos en PostgreSQL (#125)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.bd.esquema import analisis_video as tabla
from app.dominio.modelos import Prioridad
from app.video.modelos import EstadoVideo, TrabajoVideo

ESPERANDO = (EstadoVideo.PENDIENTE.value, EstadoVideo.ENVIADO.value)


def _a_trabajo(f) -> TrabajoVideo:
    return TrabajoVideo(
        f["id"], f["codigo"], f["ruta"], f["bytes"], f["creado_en"], EstadoVideo(f["estado"]),
        f["intentos"], f["reclamado_en"], f["terminado_en"],
        Prioridad(f["prioridad"]) if f["prioridad"] else None, f["confianza"],
        list(f["evidencias"]), dict(f["medidas"]), f["version_modelo"], f["motivo"],
        f["discrepancia"], bytes(f["tira"]) if f["tira"] is not None else None)


class RepositorioVideosPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def crear(self, codigo: str, ruta: str, tamano: int, ahora: datetime) -> TrabajoVideo | None:
        """El índice único de «codigo» decide si dos subidas a la vez compiten."""
        sentencia = (insert(tabla).values(codigo=codigo, ruta=ruta, bytes=tamano,
                                          estado=EstadoVideo.PENDIENTE.value, creado_en=ahora)
                     .on_conflict_do_nothing(index_elements=[tabla.c.codigo])
                     .returning(*tabla.c))
        with self._motor.begin() as conexion:
            fila = conexion.execute(sentencia).mappings().first()
        return None if fila is None else _a_trabajo(fila)

    def _uno(self, condicion) -> TrabajoVideo | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(select(tabla).where(condicion)).mappings().first()
        return None if fila is None else _a_trabajo(fila)

    def buscar(self, id_: int) -> TrabajoVideo | None:
        return self._uno(tabla.c.id == id_)

    def de_reporte(self, codigo: str) -> TrabajoVideo | None:
        return self._uno(tabla.c.codigo == codigo)

    def reclamar(self, ahora: datetime, vence_antes_de: datetime) -> TrabajoVideo | None:
        """SKIP LOCKED: si otro trabajador tiene la fila bloqueada, se salta; nadie recibe el
        mismo trabajo dos veces."""
        libre = (select(tabla.c.id)
                 .where(or_(tabla.c.estado == EstadoVideo.PENDIENTE.value,
                            and_(tabla.c.estado == EstadoVideo.ENVIADO.value,
                                 tabla.c.reclamado_en < vence_antes_de)))
                 .order_by(tabla.c.creado_en, tabla.c.id).limit(1)
                 .with_for_update(skip_locked=True))
        sentencia = (update(tabla).where(tabla.c.id == libre.scalar_subquery())
                     .values(estado=EstadoVideo.ENVIADO.value, reclamado_en=ahora)
                     .returning(*tabla.c))
        with self._motor.begin() as conexion:
            fila = conexion.execute(sentencia).mappings().first()
        return None if fila is None else _a_trabajo(fila)

    def guardar(self, trabajo: TrabajoVideo) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(update(tabla).where(tabla.c.id == trabajo.id).values(
                estado=trabajo.estado.value, intentos=trabajo.intentos,
                reclamado_en=trabajo.reclamado_en, terminado_en=trabajo.terminado_en,
                prioridad=trabajo.prioridad.value if trabajo.prioridad else None,
                confianza=trabajo.confianza, evidencias=list(trabajo.evidencias),
                medidas=dict(trabajo.medidas), version_modelo=trabajo.version_modelo,
                motivo=trabajo.motivo, discrepancia=trabajo.discrepancia, tira=trabajo.tira))

    def esperando_desde_antes(self, limite: datetime) -> list[TrabajoVideo]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(tabla).where(
                tabla.c.estado.in_(ESPERANDO), tabla.c.creado_en < limite)
                .order_by(tabla.c.id)).mappings().all()
        return [_a_trabajo(f) for f in filas]
