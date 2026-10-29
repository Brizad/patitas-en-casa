"""Refugios en PostgreSQL (fase 1, #67, RF-14)."""
from __future__ import annotations

from sqlalchemy import Engine, insert, select

from app.bd.esquema import refugios
from app.dominio.modelos import Refugio


class RepositorioRefugiosPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def crear(self, nombre: str, capacidad: int) -> Refugio:
        with self._motor.begin() as conexion:
            refugio_id = conexion.execute(
                insert(refugios).values(nombre=nombre, capacidad=capacidad)
                .returning(refugios.c.id)).scalar_one()
        return Refugio(nombre, capacidad, id=refugio_id)

    def todos(self) -> list[Refugio]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(refugios).order_by(refugios.c.id)).all()
        return [Refugio(f.nombre, f.capacidad, f.ocupados, id=f.id) for f in filas]

    def existe(self, refugio_id: int) -> bool:
        with self._motor.connect() as conexion:
            return conexion.execute(
                select(refugios.c.id).where(refugios.c.id == refugio_id)).first() is not None
