"""Adopción en PostgreSQL (fase 3, #85)."""
from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert

from app.adopciones.modelos import PerfilAdoptante, Vivienda
from app.bd.esquema import perfiles_adoptante


class RepositorioAdopcionesPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def guardar_perfil(self, perfil: PerfilAdoptante) -> None:
        fila = {"correo": perfil.correo, "vivienda": perfil.vivienda.value,
                "tiene_patio": perfil.tiene_patio, "hay_ninos": perfil.hay_ninos,
                "otros_animales": perfil.otros_animales,
                "horas_solo_al_dia": perfil.horas_solo_al_dia,
                "experiencia": perfil.experiencia,
                "acepta_seguimiento": perfil.acepta_seguimiento,
                "actualizado_en": perfil.actualizado_en}
        sentencia = insert(perfiles_adoptante).values(**fila)
        sentencia = sentencia.on_conflict_do_update(
            index_elements=[perfiles_adoptante.c.correo],
            set_={k: sentencia.excluded[k] for k in fila if k != "correo"})
        with self._motor.begin() as conexion:
            conexion.execute(sentencia)

    def perfil(self, correo: str) -> PerfilAdoptante | None:
        with self._motor.connect() as conexion:
            f = conexion.execute(select(perfiles_adoptante).where(
                perfiles_adoptante.c.correo == correo)).mappings().first()
        if f is None:
            return None
        return PerfilAdoptante(
            correo=f["correo"], vivienda=Vivienda(f["vivienda"]), tiene_patio=f["tiene_patio"],
            hay_ninos=f["hay_ninos"], otros_animales=f["otros_animales"],
            horas_solo_al_dia=f["horas_solo_al_dia"], experiencia=f["experiencia"],
            acepta_seguimiento=f["acepta_seguimiento"], actualizado_en=f["actualizado_en"])
