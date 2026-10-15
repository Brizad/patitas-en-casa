"""Fixtures compartidas: base de datos de pruebas en PostgreSQL (DT-01).

Sin PostgreSQL configurado, las pruebas que lo usan se omiten. Con
PATITAS_EXIGIR_POSTGRES=1 (lo usa el CI) fallan, para que nunca se omitan en silencio.
"""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from app.ajustes import ConfiguracionIncompleta, cargar_ajustes
from app.bd.migraciones import aplicar_migraciones


def _sin_postgres(motivo: str):
    if os.environ.get("PATITAS_EXIGIR_POSTGRES") == "1":
        pytest.fail(f"PostgreSQL es obligatorio en este entorno: {motivo}")
    pytest.skip(f"PostgreSQL no disponible: {motivo}")


@pytest.fixture(scope="session")
def motor_pruebas():
    try:
        ajustes = cargar_ajustes()
    except ConfiguracionIncompleta as error:
        _sin_postgres(str(error))
    if ajustes.db_pruebas == ajustes.db:
        pytest.fail("POSTGRES_DB_PRUEBAS no puede ser la base de la aplicación: "
                    "las pruebas borran datos.")
    motor = create_engine(ajustes.url(pruebas=True))
    try:
        with motor.connect():
            pass
    except OperationalError as error:
        motor.dispose()
        _sin_postgres(str(error.orig).strip())
    aplicar_migraciones(motor)
    yield motor
    motor.dispose()


@pytest.fixture
def bd_limpia(motor_pruebas):
    """Cada prueba empieza con la tabla vacía."""
    with motor_pruebas.begin() as conexion:
        conexion.execute(text("TRUNCATE TABLE reportes"))
    return motor_pruebas
