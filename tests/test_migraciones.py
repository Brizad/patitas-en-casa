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


def test_la_migracion_crea_el_refugio_demo(motor_pruebas):
    """La revisión 0002 deja un refugio listo para usar la app recién instalada."""
    revertir_migraciones(motor_pruebas, "0001")
    aplicar_migraciones(motor_pruebas)
    with motor_pruebas.connect() as conexion:
        filas = conexion.execute(text("SELECT nombre, capacidad, ocupados FROM refugios")).all()
    assert [tuple(f) for f in filas] == [("Refugio demo Cúcuta", 40, 0)]


@pytest.mark.parametrize("capacidad, ocupados", [(0, 0), (10, -1), (10, 11)])
def test_la_base_rechaza_refugios_invalidos(bd_limpia, capacidad, ocupados):
    """Invariante de BUG-04 también en la base: 0 <= ocupados <= capacidad, capacidad > 0."""
    with pytest.raises(IntegrityError), bd_limpia.begin() as conexion:
        conexion.execute(text("INSERT INTO refugios (nombre, capacidad, ocupados) "
                              "VALUES ('Otro', :c, :o)"), {"c": capacidad, "o": ocupados})


def test_la_base_rechaza_especies_desconocidas(bd_limpia):
    with pytest.raises(IntegrityError), bd_limpia.begin() as conexion:
        conexion.execute(text("INSERT INTO animales (refugio_id, nombre, especie, estado_salud) "
                              "VALUES (1, 'Piolín', 'canario', 'sano')"))

@pytest.mark.parametrize("final, justificacion, valido", [
    ("critica", None, True),                   # confirma la sugerida: sin justificación
    ("alta", "Camina con dificultad", True),   # ajuste justificado
    ("alta", None, False),                     # ajuste sin justificación (RN-16)
    ("alta", "  corta  ", False),              # menos de 10 caracteres sin espacios
])
def test_la_base_exige_justificacion_al_ajustar(bd_limpia, final, justificacion, valido):
    insertar(bd_limpia)
    sentencia = text(
        "INSERT INTO decisiones_triaje (reporte_codigo, veterinario, prioridad_sugerida, "
        "prioridad_final, justificacion) VALUES ('ABCD1234', 'vet@patitas.co', 'critica', "
        ":final, :justificacion)")
    if valido:
        with bd_limpia.begin() as conexion:
            conexion.execute(sentencia, {"final": final, "justificacion": justificacion})
    else:
        with pytest.raises(IntegrityError), bd_limpia.begin() as conexion:
            conexion.execute(sentencia, {"final": final, "justificacion": justificacion})


# --- #63: tabla avisos (outbox) ---------------------------------------------------------

def insertar_aviso(motor, **cambios):
    fila = {"reporte_codigo": "ABCD1234", "destinatario": "ana@rescate.co",
            "mensaje": "Rescate crítico ABCD1234", "estado": "pendiente", "intentos": 0,
            **cambios}
    with motor.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO avisos (reporte_codigo, destinatario, mensaje, estado, intentos, "
            "creado_en, proximo_intento_en) VALUES (:reporte_codigo, :destinatario, "
            ":mensaje, :estado, :intentos, now(), now())"), fila)


def test_aviso_valido_se_inserta(bd_limpia):
    insertar(bd_limpia)
    insertar_aviso(bd_limpia)


@pytest.mark.parametrize("cambios", [
    {"estado": "perdido"},
    {"intentos": -1},
    {"reporte_codigo": "NOEXISTE"},  # FK: no hay aviso sin reporte
])
def test_la_base_rechaza_avisos_invalidos(bd_limpia, cambios):
    insertar(bd_limpia)
    with pytest.raises(IntegrityError):
        insertar_aviso(bd_limpia, **cambios)


def test_un_solo_aviso_por_rescatista_y_reporte(bd_limpia):
    insertar(bd_limpia)
    insertar_aviso(bd_limpia)
    with pytest.raises(IntegrityError):
        insertar_aviso(bd_limpia)
