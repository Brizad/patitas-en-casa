"""Intentos fallidos de inicio de sesión en PostgreSQL (DT-06).

En la base el límite vale para todos los procesos de la API y sobrevive a un reinicio.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, delete, insert, select

from app.bd.esquema import intentos_fallidos


class RepositorioIntentosPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def registrar_fallo(self, clave: str, momento: datetime) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(insert(intentos_fallidos).values(clave=clave, ocurrido_en=momento))

    def fallos_desde(self, clave: str, desde: datetime) -> list[datetime]:
        with self._motor.connect() as conexion:
            return list(conexion.execute(
                select(intentos_fallidos.c.ocurrido_en)
                .where(intentos_fallidos.c.clave == clave,
                       intentos_fallidos.c.ocurrido_en > desde)
                .order_by(intentos_fallidos.c.ocurrido_en)
            ).scalars())

    def limpiar(self, clave: str) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(delete(intentos_fallidos).where(intentos_fallidos.c.clave == clave))

    def purgar_antes_de(self, momento: datetime) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(delete(intentos_fallidos)
                             .where(intentos_fallidos.c.ocurrido_en < momento))
