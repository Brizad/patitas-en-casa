"""RF-20 / D-04 (#75): cada reporte y cada decisión guardan la versión del modelo que sugirió.

Así, cuando el clasificador por reglas se reemplace por un modelo entrenado (DT-04), la
bitácora sigue diciendo qué versión sugirió cada prioridad y se pueden comparar.
"""
import pytest
from sqlalchemy import text

from app.dominio.modelos import EstadoReporte, Prioridad, Reporte, Rol, Ubicacion, Usuario
from app.reportes.confirmacion import ServicioConfirmacion
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.triaje.clasificador import VERSION
from app.triaje.servicio import ServicioTriaje

VET = Usuario("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, hash_contrasena="x")


def reporte():
    return Reporte(codigo="ABCD1234", descripcion="Perro atropellado, sangra mucho en la vía",
                   ubicacion=Ubicacion(direccion="Calle 10"))


def test_el_triaje_anota_la_version_del_clasificador():
    evaluado = ServicioTriaje().evaluar(reporte())
    assert evaluado.version_modelo == VERSION == "reglas-v0"


def test_en_falla_segura_no_hay_version_porque_ningun_modelo_sugirio():
    def roto(_texto):
        raise RuntimeError("caído")
    evaluado = ServicioTriaje(roto).evaluar(reporte())
    assert evaluado.estado == EstadoReporte.SIN_CLASIFICAR and evaluado.version_modelo is None


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioPostgres(request.getfixturevalue("bd_limpia"))
    return RepositorioEnMemoria()


def test_la_decision_copia_la_version_y_ambas_se_guardan(repositorio):
    repositorio.guardar(ServicioTriaje().evaluar(reporte()))
    assert repositorio.buscar("ABCD1234").version_modelo == "reglas-v0"
    ServicioConfirmacion(repositorio).confirmar("ABCD1234", VET)
    (decision,) = repositorio.decisiones("ABCD1234")
    assert decision.version_modelo == "reglas-v0"
    assert decision.prioridad_final == Prioridad.CRITICA


@pytest.mark.postgres
def test_las_filas_anteriores_quedan_sin_version(bd_limpia):
    """Migración aditiva: los reportes viejos no tienen versión (NULL), no una inventada."""
    with bd_limpia.begin() as conexion:
        conexion.execute(text(
            "INSERT INTO reportes (codigo, descripcion, direccion, estado, creado_en) "
            "VALUES ('VIEJO123', 'Reporte de antes de la migración 0012', 'Calle 1', "
            "'recibido', now())"))
    assert RepositorioPostgres(bd_limpia).buscar("VIEJO123").version_modelo is None
