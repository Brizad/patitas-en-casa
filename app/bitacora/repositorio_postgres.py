"""Bitácora en PostgreSQL (RF-32, #102): solo INSERT y SELECT."""
from __future__ import annotations

from sqlalchemy import Engine, insert, select

from app.bd.esquema import bitacora
from app.bitacora.repositorio import Evento


class RepositorioBitacoraPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def registrar(self, evento: Evento) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(insert(bitacora).values(
                momento=evento.momento, actor=evento.actor, accion=evento.accion,
                objeto=evento.objeto, estado_http=evento.estado_http,
                valor_anterior=evento.anterior, valor_nuevo=evento.nuevo))

    def recientes(self, limite: int = 100) -> list[Evento]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(bitacora).order_by(bitacora.c.id.desc())
                                     .limit(limite)).mappings()
            return [_evento(f) for f in filas]

    def de_actor(self, actor: str, accion: str, limite: int = 50) -> list[Evento]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(bitacora).where(
                bitacora.c.actor == actor, bitacora.c.accion == accion)
                .order_by(bitacora.c.id.desc()).limit(limite)).mappings()
            return [_evento(f) for f in filas]


def _evento(f) -> Evento:
    return Evento(actor=f["actor"], accion=f["accion"], objeto=dict(f["objeto"]),
                  estado_http=f["estado_http"], momento=f["momento"],
                  anterior=f["valor_anterior"], nuevo=f["valor_nuevo"])
