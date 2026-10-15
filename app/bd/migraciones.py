"""Aplicar, revertir o verificar las migraciones de Alembic desde Python."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, Engine

RAIZ = Path(__file__).resolve().parents[2]


class BaseDeDatosDesactualizada(RuntimeError):
    pass


def _config(conexion: Connection | None = None) -> Config:
    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "migraciones"))
    config.attributes["connection"] = conexion
    return config


def aplicar_migraciones(motor: Engine, revision: str = "head") -> None:
    with motor.begin() as conexion:
        command.upgrade(_config(conexion), revision)


def revertir_migraciones(motor: Engine, revision: str) -> None:
    with motor.begin() as conexion:
        command.downgrade(_config(conexion), revision)


def verificar_migraciones(motor: Engine) -> None:
    """Falla al arrancar si la base no está en la última migración del código."""
    esperada = ScriptDirectory.from_config(_config()).get_current_head()
    with motor.connect() as conexion:
        actual = MigrationContext.configure(conexion).get_current_revision()
    if actual != esperada:
        raise BaseDeDatosDesactualizada(
            f"La base está en la migración {actual or 'ninguna'} y el código espera "
            f"{esperada}: ejecuta 'alembic upgrade head'."
        )
