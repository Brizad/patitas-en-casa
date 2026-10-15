"""Entorno de Alembic: de dónde sale la conexión y qué esquema se compara."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine

from app.ajustes import cargar_ajustes
from app.bd.esquema import metadata

config = context.config


def ejecutar(conexion) -> None:
    context.configure(connection=conexion, target_metadata=metadata)
    with context.begin_transaction():
        context.run_migrations()


def migrar_en_linea() -> None:
    # Desde las pruebas (app/bd/migraciones.py) llega una conexión ya abierta.
    conexion = config.attributes.get("connection")
    if conexion is not None:
        ejecutar(conexion)
        return
    # Desde la consola: la URL sale del .env; -x pruebas=true usa POSTGRES_DB_PRUEBAS.
    if config.config_file_name:
        fileConfig(config.config_file_name)
    pruebas = context.get_x_argument(as_dictionary=True).get("pruebas") == "true"
    motor = create_engine(cargar_ajustes().url(pruebas=pruebas))
    try:
        with motor.begin() as conexion:
            ejecutar(conexion)
    finally:
        motor.dispose()


if context.is_offline_mode():
    raise SystemExit("El modo sin conexión (--sql) no se usa en este proyecto.")
migrar_en_linea()
