"""Configuración de PostgreSQL leída del entorno / .env (DT-01, paso 1)."""
import pytest

from app.ajustes import ConfiguracionIncompleta, cargar_ajustes

VARIABLES = ["POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_USER", "POSTGRES_PASSWORD",
             "POSTGRES_DB", "POSTGRES_DB_PRUEBAS"]


@pytest.fixture(autouse=True)
def entorno_limpio(monkeypatch):
    """Ninguna prueba depende de las variables o del .env de quien las ejecuta."""
    for variable in VARIABLES:
        monkeypatch.delenv(variable, raising=False)


def ajustes(monkeypatch, **variables):
    for nombre, valor in variables.items():
        monkeypatch.setenv(nombre, valor)
    return cargar_ajustes(archivo_env=None)


def test_lee_las_variables_del_entorno(monkeypatch):
    a = ajustes(monkeypatch, POSTGRES_HOST="db.local", POSTGRES_PORT="6543",
                POSTGRES_USER="patitas", POSTGRES_PASSWORD="clave", POSTGRES_DB="otra")
    assert (a.host, a.port, a.user, a.db) == ("db.local", 6543, "patitas", "otra")


def test_valores_por_defecto_del_entorno_local(monkeypatch):
    a = ajustes(monkeypatch, POSTGRES_PASSWORD="clave")
    assert (a.host, a.port, a.user) == ("localhost", 5432, "postgres")
    assert (a.db, a.db_pruebas) == ("patitas", "patitas_test")


def test_sin_contrasena_da_un_error_entendible(monkeypatch):
    with pytest.raises(ConfiguracionIncompleta, match="POSTGRES_PASSWORD.*\\.env\\.example"):
        cargar_ajustes(archivo_env=None)


def test_la_contrasena_no_aparece_al_imprimir_los_ajustes(monkeypatch):
    a = ajustes(monkeypatch, POSTGRES_PASSWORD="super-secreta")
    assert "super-secreta" not in repr(a)
    assert "super-secreta" not in str(a)


def test_url_de_la_aplicacion_y_de_las_pruebas(monkeypatch):
    a = ajustes(monkeypatch, POSTGRES_PASSWORD="clave")
    assert a.url() == "postgresql+psycopg://postgres:clave@localhost:5432/patitas"
    assert a.url(pruebas=True).endswith("/patitas_test")


def test_url_escapa_caracteres_especiales_de_la_contrasena(monkeypatch):
    a = ajustes(monkeypatch, POSTGRES_PASSWORD="p@ss:w/rd#1")
    assert "p%40ss%3Aw%2Frd%231@localhost" in a.url()
