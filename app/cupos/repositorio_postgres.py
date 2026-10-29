"""Cupos del refugio en PostgreSQL (DT-05).

El cupo se toma con un UPDATE condicional: PostgreSQL bloquea la fila del refugio, así que
dos ingresos simultáneos no pueden pasar ambos la condición "ocupados < capacidad", aunque
lleguen desde procesos distintos. El CHECK de la tabla es la última barrera.
"""
from __future__ import annotations

from sqlalchemy import Engine, insert, select, update

from app.bd.esquema import animales, refugios
from app.dominio.modelos import Animal, Refugio


class RepositorioCuposPostgres:
    def __init__(self, motor: Engine, refugio_id: int) -> None:
        self._motor = motor
        self._refugio_id = refugio_id

    @classmethod
    def primer_refugio(cls, motor: Engine) -> RepositorioCuposPostgres:
        """El MVP maneja un solo refugio: el de menor id (lo crea la migración 0002)."""
        with motor.connect() as conexion:
            refugio_id = conexion.execute(
                select(refugios.c.id).order_by(refugios.c.id).limit(1)
            ).scalar()
        if refugio_id is None:
            raise LookupError("No hay ningún refugio registrado: ejecuta 'alembic upgrade head'.")
        return cls(motor, refugio_id)

    def para_refugio(self, refugio_id: int) -> RepositorioCuposPostgres:
        return RepositorioCuposPostgres(self._motor, refugio_id)

    def refugio(self) -> Refugio:
        with self._motor.connect() as conexion:
            fila = conexion.execute(
                select(refugios.c.nombre, refugios.c.capacidad, refugios.c.ocupados)
                .where(refugios.c.id == self._refugio_id)
            ).one()
        return Refugio(fila.nombre, fila.capacidad, fila.ocupados)

    def ocupar_cupo(self, animal: Animal) -> Refugio | None:
        with self._motor.begin() as conexion:
            fila = conexion.execute(
                update(refugios)
                .where(refugios.c.id == self._refugio_id,
                       refugios.c.ocupados < refugios.c.capacidad)
                .values(ocupados=refugios.c.ocupados + 1)
                .returning(refugios.c.nombre, refugios.c.capacidad, refugios.c.ocupados)
            ).first()
            if fila is None:
                return None
            conexion.execute(insert(animales).values(
                refugio_id=self._refugio_id, nombre=animal.nombre,
                especie=animal.especie.value, estado_salud=animal.estado_salud,
                vacunado=animal.vacunado, esterilizado=animal.esterilizado,
            ))
        return Refugio(fila.nombre, fila.capacidad, fila.ocupados)
