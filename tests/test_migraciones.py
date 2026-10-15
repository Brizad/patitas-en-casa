"""Migraciones de Alembic y restricciones de la tabla reportes (DT-01, paso 3)."""
import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.bd.esquema import metadata
from app.bd.migraciones import aplicar_migraciones, revertir_migraciones
from app.dominio.modelos import EstadoReporte, Prioridad

pytestmark = pytest.mark.postgres

FILA_VALIDA = {
    "codigo": "ABCD1234", "descripcion": "Perro atropellado frente al parque",
    "latitud": 7.89, "longitud": -72.5, "direccion": None, "video_segundos": 30,
    "estado": "clasificado", "prioridad": "critica", "confianza": 0.8,
}


def insertar(motor, **cambios):
    fila = {**FILA_VALIDA, **cambios}
    with motor.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO reportes (codigo, descripcion, latitud, longitud, direccion, "
            "video_segundos, estado, prioridad, confianza, creado_en) VALUES (:codigo, "
            ":descripcion, :latitud, :longitud, :direccion, :video_segundos, :estado, "
            ":prioridad, :confianza, now())"), fila)


def test_la_migracion_sube_baja_y_vuelve_a_subir(motor_pruebas):
    revertir_migraciones(motor_pruebas, "base")
    assert "reportes" not in inspect(motor_pruebas).get_table_names()
    aplicar_migraciones(motor_pruebas)
    assert "reportes" in inspect(motor_pruebas).get_table_names()


def test_el_esquema_migrado_coincide_con_app_bd_esquema(motor_pruebas):
    """Si alguien cambia app/bd/esquema.py sin crear una migración, esta prueba falla."""
    with motor_pruebas.connect() as conexion:
        diferencias = compare_metadata(MigrationContext.configure(conexion), metadata)
    assert diferencias == []


def test_fila_valida_se_inserta(bd_limpia):
    insertar(bd_limpia)


@pytest.mark.parametrize("estado", list(EstadoReporte))
def test_la_base_acepta_todos_los_estados_del_dominio(bd_limpia, estado):
    insertar(bd_limpia, estado=estado.value)


@pytest.mark.parametrize("prioridad", [*Prioridad, None])
def test_la_base_acepta_todas_las_prioridades_del_dominio(bd_limpia, prioridad):
    insertar(bd_limpia, prioridad=prioridad.value if prioridad else None)


@pytest.mark.parametrize("cambios", [
    {"estado": "inventado"},
    {"prioridad": "urgente"},  # cabe en la columna: lo rechaza el CHECK, no el largo
    {"confianza": 1.5},
    {"confianza": -0.1},
    {"video_segundos": -1},
    {"latitud": None, "longitud": None, "direccion": None},  # sin ubicación (RN-01)
    {"latitud": 7.89, "longitud": None, "direccion": None},  # GPS incompleto
])
def test_la_base_rechaza_datos_invalidos(bd_limpia, cambios):
    with pytest.raises(IntegrityError):
        insertar(bd_limpia, **cambios)


def test_la_base_rechaza_codigos_repetidos(bd_limpia):
    insertar(bd_limpia)
    with pytest.raises(IntegrityError):
        insertar(bd_limpia)
