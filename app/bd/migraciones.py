"""Aplicar o revertir las migraciones de Alembic desde Python (pruebas y arranque)."""
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine

RAIZ = Path(__file__).resolve().parents[2]


def _config(conexion: Connection) -> Config:
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
