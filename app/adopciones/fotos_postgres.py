"""Fotos de los animales en PostgreSQL (RF-25, #115)."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert

from app.bd.esquema import fotos_animales


class RepositorioFotosPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def guardar(self, animal_id: int, tipo: str, datos: bytes) -> None:
        sentencia = insert(fotos_animales).values(
            animal_id=animal_id, tipo=tipo, datos=datos, guardada_en=datetime.now(UTC))
        sentencia = sentencia.on_conflict_do_update(
            index_elements=[fotos_animales.c.animal_id],
            set_={"tipo": tipo, "datos": datos, "guardada_en": sentencia.excluded.guardada_en})
        with self._motor.begin() as conexion:
            conexion.execute(sentencia)

    def foto(self, animal_id: int) -> tuple[str, bytes] | None:
        with self._motor.connect() as conexion:
            f = conexion.execute(select(fotos_animales.c.tipo, fotos_animales.c.datos).where(
                fotos_animales.c.animal_id == animal_id)).first()
        return None if f is None else (f.tipo, bytes(f.datos))

    def con_foto(self) -> set[int]:
        with self._motor.connect() as conexion:
            return set(conexion.execute(select(fotos_animales.c.animal_id)).scalars())
