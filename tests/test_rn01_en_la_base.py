"""RN-01 en la base (migración 0035): la descripción de 20 caracteres o más ya no depende solo
del código. Prueba de contrato: la base y `ServicioReportes` aceptan y rechazan lo mismo."""
import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.bd.esquema import reportes
from app.bd.migraciones import aplicar_migraciones, revertir_migraciones
from app.dominio.modelos import Ubicacion
from app.reportes.servicio import MIN_CARACTERES_DESCRIPCION, ReporteInvalido, ServicioReportes

NOMBRE = "ck_reportes_descripcion"
RUTA = Path(__file__).parents[1] / "migraciones" / "versions" / "0035_check_rn01_descripcion.py"
JUSTA = "Perro herido aquí ya"  # 20 caracteres exactos
CASOS = [  # (descripción, ¿cumple RN-01?)
    (JUSTA, True),
    (JUSTA[:-1], False),
    ("   " + JUSTA[:-1] + "      ", False),  # los espacios de los extremos no cuentan
    ("\t" + JUSTA + "\n", True),
    ("Perro que cojea y no apoya la pata izquierda", True),
    ("", False),
]


def _migracion():
    especificacion = importlib.util.spec_from_file_location("migracion_0035", RUTA)
    modulo = importlib.util.module_from_spec(especificacion)
    especificacion.loader.exec_module(modulo)
    return modulo


def _insertar(motor, codigo: str, descripcion: str) -> None:
    with motor.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO reportes (codigo, descripcion, direccion, estado, creado_en) "
            "VALUES (:c, :d, 'Calle 10 # 5-20', 'recibido', now())"),
            {"c": codigo, "d": descripcion})


def _validada(motor) -> bool:
    with motor.connect() as conexion:
        consulta = text("SELECT convalidated FROM pg_constraint WHERE conname = :n")
        return conexion.execute(consulta, {"n": NOMBRE}).scalar_one()


# --- Sin base: el esquema, la migración y el servicio dicen lo mismo ---

def test_el_minimo_de_la_base_es_el_del_servicio():
    assert len(JUSTA) == MIN_CARACTERES_DESCRIPCION == 20
    migracion = _migracion()
    del_esquema = next(c for c in reportes.constraints if c.name == NOMBRE)
    assert str(del_esquema.sqltext) == migracion.CONDICION
    assert f">= {MIN_CARACTERES_DESCRIPCION}" in migracion.CONDICION


def test_la_migracion_es_aditiva_y_no_valida_las_filas_viejas_de_entrada():
    fuente = RUTA.read_text("utf-8")
    assert "NOT VALID" in fuente and "VALIDATE CONSTRAINT" in fuente
    assert "DELETE" not in fuente and "UPDATE reportes" not in fuente  # nunca toca los datos


@pytest.mark.parametrize(("descripcion", "cumple"), CASOS)
def test_el_servicio_aplica_rn01(descripcion, cumple):
    ubicacion = Ubicacion(direccion="Calle 10 # 5-20")
    if cumple:
        ServicioReportes.validar(descripcion, ubicacion, None, None)
    else:
        with pytest.raises(ReporteInvalido):
            ServicioReportes.validar(descripcion, ubicacion, None, None)


# --- Con PostgreSQL: la base decide igual que el servicio ---

@pytest.mark.postgres
@pytest.mark.parametrize(("descripcion", "cumple"), CASOS)
def test_la_base_aplica_rn01_igual_que_el_servicio(bd_limpia, descripcion, cumple):
    if cumple:
        _insertar(bd_limpia, "RN010001", descripcion)
    else:
        with pytest.raises(IntegrityError, match=NOMBRE):
            _insertar(bd_limpia, "RN010001", descripcion)


@pytest.mark.postgres
def test_tampoco_se_puede_acortar_una_descripcion_ya_guardada(bd_limpia):
    _insertar(bd_limpia, "RN010002", JUSTA)
    with pytest.raises(IntegrityError, match=NOMBRE), bd_limpia.begin() as conexion:
        conexion.execute(text(
            "UPDATE reportes SET descripcion = 'corta' WHERE codigo = 'RN010002'"))


@pytest.mark.postgres
def test_con_datos_que_cumplen_la_restriccion_queda_validada(bd_limpia):
    assert _validada(bd_limpia) is True


@pytest.mark.postgres
def test_con_filas_viejas_cortas_no_se_borra_nada_y_queda_sin_validar(bd_limpia):
    """El caso delicado: una base con reportes anteriores que no cumplen. La migración no
    falla ni toca esas filas; la regla rige para lo nuevo."""
    try:
        revertir_migraciones(bd_limpia, "0034")
        _insertar(bd_limpia, "VIEJO001", "muy corta")
        aplicar_migraciones(bd_limpia)
        assert _validada(bd_limpia) is False
        with bd_limpia.connect() as conexion:
            assert conexion.execute(text(
                "SELECT descripcion FROM reportes WHERE codigo = 'VIEJO001'")).scalar_one() == (
                    "muy corta")
        with pytest.raises(IntegrityError, match=NOMBRE):
            _insertar(bd_limpia, "NUEVO001", "también corta")
        _insertar(bd_limpia, "NUEVO002", JUSTA)
    finally:  # la base de pruebas vuelve a quedar con la restricción validada
        revertir_migraciones(bd_limpia, "0034")
        with bd_limpia.begin() as conexion:
            conexion.execute(text("TRUNCATE TABLE reportes CASCADE"))
        aplicar_migraciones(bd_limpia)
