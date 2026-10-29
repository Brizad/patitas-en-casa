"""Cupos del refugio en PostgreSQL (DT-05).

El cupo se toma con un UPDATE condicional: PostgreSQL bloquea la fila del refugio, así que
dos ingresos simultáneos no pueden pasar ambos la condición "ocupados < capacidad", aunque
lleguen desde procesos distintos. El CHECK de la tabla es la última barrera.
"""
from __future__ import annotations

from sqlalchemy import Engine, func, insert, select, update

from app.bd.esquema import animales, historial_clinico, refugios
from app.dominio.modelos import (
    Animal,
    Especie,
    MotivoEgreso,
    NotaClinica,
    Refugio,
    TipoNota,
)


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
            nuevo = conexion.execute(insert(animales).values(
                refugio_id=self._refugio_id, nombre=animal.nombre,
                especie=animal.especie.value, estado_salud=animal.estado_salud,
                vacunado=animal.vacunado, esterilizado=animal.esterilizado,
            ).returning(animales.c.id, animales.c.ingresado_en)).one()
        animal.id, animal.ingresado_en = nuevo.id, nuevo.ingresado_en
        return Refugio(fila.nombre, fila.capacidad, fila.ocupados)

    def animales(self) -> list[Animal]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(animales).where(
                animales.c.refugio_id == self._refugio_id).order_by(animales.c.id)).mappings()
            return [_animal(f) for f in filas]

    def animal(self, animal_id: int) -> Animal | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(select(animales).where(
                animales.c.id == animal_id, animales.c.refugio_id == self._refugio_id)
            ).mappings().first()
        return None if fila is None else _animal(fila)

    def agregar_nota(self, nota: NotaClinica) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(insert(historial_clinico).values(
                animal_id=nota.animal_id, autor=nota.autor, tipo=nota.tipo.value,
                texto=nota.texto, registrada_en=nota.registrada_en))

    def reingresar(self, animal_id: int) -> Refugio | None:
        try:
            with self._motor.begin() as conexion:  # SinCupo deshace la transacción
                return reingresar_en(conexion, animal_id, self._refugio_id)
        except SinCupo:
            return None

    def egresar(self, animal_id: int, motivo: MotivoEgreso) -> Refugio | None:
        """Dos UPDATE condicionales en una transacción: el animal solo se marca si sigue en
        el refugio (dos egresos simultáneos no liberan dos cupos) y el cupo baja después."""
        with self._motor.begin() as conexion:
            marcado = conexion.execute(
                update(animales)
                .where(animales.c.id == animal_id, animales.c.refugio_id == self._refugio_id,
                       animales.c.egresado_en.is_(None))
                .values(egresado_en=func.now(), motivo_egreso=motivo.value))
            if marcado.rowcount == 0:
                return None
            fila = conexion.execute(
                update(refugios).where(refugios.c.id == self._refugio_id)
                .values(ocupados=refugios.c.ocupados - 1)
                .returning(refugios.c.nombre, refugios.c.capacidad, refugios.c.ocupados)).one()
        return Refugio(fila.nombre, fila.capacidad, fila.ocupados)

    def historial(self, animal_id: int) -> list[NotaClinica]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(historial_clinico).where(
                historial_clinico.c.animal_id == animal_id).order_by(historial_clinico.c.id)
            ).mappings()
            return [NotaClinica(animal_id=f["animal_id"], autor=f["autor"],
                                tipo=TipoNota(f["tipo"]), texto=f["texto"],
                                registrada_en=f["registrada_en"]) for f in filas]


def _animal(fila) -> Animal:
    return Animal(nombre=fila["nombre"], especie=Especie(fila["especie"]),
                  estado_salud=fila["estado_salud"], vacunado=fila["vacunado"],
                  esterilizado=fila["esterilizado"], id=fila["id"],
                  ingresado_en=fila["ingresado_en"], egresado_en=fila["egresado_en"],
                  motivo_egreso=MotivoEgreso(fila["motivo_egreso"])
                  if fila["motivo_egreso"] else None)


class SinCupo(Exception):
    """Para deshacer la transacción: el animal devuelto no cabe (RN-04)."""


def reingresar_en(conexion, animal_id: int, refugio_id: int | None = None) -> Refugio | None:
    """Reingreso dentro de una transacción abierta (la usa también la devolución). Si no hay
    cupo lanza SinCupo para que la transacción entera se deshaga."""
    condicion = [animales.c.id == animal_id, animales.c.egresado_en.is_not(None)]
    if refugio_id is not None:
        condicion.append(animales.c.refugio_id == refugio_id)
    refugio = conexion.execute(update(animales).where(*condicion).values(
        egresado_en=None, motivo_egreso=None).returning(animales.c.refugio_id)).scalar()
    if refugio is None:
        return None
    fila = conexion.execute(
        update(refugios).where(refugios.c.id == refugio,
                               refugios.c.ocupados < refugios.c.capacidad)
        .values(ocupados=refugios.c.ocupados + 1)
        .returning(refugios.c.nombre, refugios.c.capacidad, refugios.c.ocupados)).first()
    if fila is None:
        raise SinCupo
    return Refugio(fila.nombre, fila.capacidad, fila.ocupados)
