"""La API conectada a PostgreSQL (DT-01, paso 4): los reportes sobreviven a un reinicio."""
import pytest
from fastapi.testclient import TestClient

from app.ajustes import cargar_ajustes
from app.api.main import crear_app
from app.bd.migraciones import (
    BaseDeDatosDesactualizada,
    aplicar_migraciones,
    revertir_migraciones,
)
from app.reportes.repositorio_postgres import RepositorioPostgres

pytestmark = pytest.mark.postgres

CRITICO = {"descripcion": "Perro atropellado en la avenida, está sangrando mucho",
           "latitud": 7.8939, "longitud": -72.5078}
LEVE = {"descripcion": "Gato con sarna en el andén del barrio", "direccion": "Calle 10 # 5-30"}


def cliente(motor):
    return TestClient(crear_app(RepositorioPostgres(motor)))


def usar_base_de_pruebas(monkeypatch):
    """crear_app() sin argumentos lee POSTGRES_DB: se apunta a la base de pruebas."""
    monkeypatch.setenv("POSTGRES_DB", cargar_ajustes().db_pruebas)


def test_reporte_sobrevive_a_un_reinicio_de_la_app(bd_limpia):
    codigo = cliente(bd_limpia).post("/reportes", json=CRITICO).json()["codigo"]
    respuesta = cliente(bd_limpia).get(f"/reportes/{codigo}")  # otra instancia de la app
    assert respuesta.status_code == 200
    assert respuesta.json() == {"codigo": codigo, "estado": "clasificado"}


def test_cola_lee_postgres_con_el_critico_primero(bd_limpia):
    c = cliente(bd_limpia)
    c.post("/reportes", json=LEVE)
    critico = c.post("/reportes", json=CRITICO).json()["codigo"]
    cola = cliente(bd_limpia).get("/cola", headers={"X-Rol": "veterinario"}).json()
    assert [r["codigo"] for r in cola][0] == critico
    assert len(cola) == 2


def test_crear_app_sin_argumentos_usa_postgres(bd_limpia, monkeypatch):
    usar_base_de_pruebas(monkeypatch)
    with TestClient(crear_app()) as c:
        codigo = c.post("/reportes", json=CRITICO).json()["codigo"]
    assert RepositorioPostgres(bd_limpia).buscar(codigo) is not None


def test_el_arranque_falla_si_la_base_no_esta_migrada(motor_pruebas, monkeypatch):
    usar_base_de_pruebas(monkeypatch)
    revertir_migraciones(motor_pruebas, "base")
    try:
        with pytest.raises(BaseDeDatosDesactualizada, match="alembic upgrade head"):
            crear_app()
    finally:
        aplicar_migraciones(motor_pruebas)
