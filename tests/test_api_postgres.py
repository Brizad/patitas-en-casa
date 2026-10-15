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
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Rol
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios
from tests.conftest import preparar_refugio

pytestmark = pytest.mark.postgres

CRITICO = {"descripcion": "Perro atropellado en la avenida, está sangrando mucho",
           "latitud": 7.8939, "longitud": -72.5078}
LEVE = {"descripcion": "Gato con sarna en el andén del barrio", "direccion": "Calle 10 # 5-30"}
INGRESO = {"nombre": "Canela", "especie": "gato", "estado_salud": "desnutrición leve"}
# Valores falsos, solo para pruebas.
SECRETO_PRUEBAS = "secreto-de-pruebas-con-mas-de-32-caracteres"
CLAVE = "clave-de-prueba-larga"


def cliente(motor):
    return TestClient(crear_app(RepositorioPostgres(motor),
                                RepositorioCuposPostgres.primer_refugio(motor),
                                repositorio_usuarios=RepositorioUsuariosPostgres(motor),
                                emisor_tokens=EmisorTokens(SECRETO_PRUEBAS)))


def sesion(c, motor):
    """Registra una coordinadora en la base de pruebas e inicia sesión con ella."""
    ServicioUsuarios(RepositorioUsuariosPostgres(motor)).registrar(
        "coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    token = c.post("/auth/token", data={"username": "coord@patitas.co", "password": CLAVE})
    return {"Authorization": f"Bearer {token.json()['access_token']}"}


def usar_base_de_pruebas(monkeypatch):
    """crear_app() sin argumentos lee el entorno: base de pruebas y clave JWT falsa."""
    monkeypatch.setenv("POSTGRES_DB", cargar_ajustes().db_pruebas)
    monkeypatch.setenv("PATITAS_JWT_SECRETO", SECRETO_PRUEBAS)


def test_reporte_sobrevive_a_un_reinicio_de_la_app(bd_limpia):
    codigo = cliente(bd_limpia).post("/reportes", json=CRITICO).json()["codigo"]
    respuesta = cliente(bd_limpia).get(f"/reportes/{codigo}")  # otra instancia de la app
    assert respuesta.status_code == 200
    assert respuesta.json() == {"codigo": codigo, "estado": "clasificado"}


def test_cola_lee_postgres_con_el_critico_primero(bd_limpia):
    c = cliente(bd_limpia)
    c.post("/reportes", json=LEVE)
    critico = c.post("/reportes", json=CRITICO).json()["codigo"]
    otra = cliente(bd_limpia)
    cola = otra.get("/cola", headers=sesion(otra, bd_limpia)).json()
    assert [r["codigo"] for r in cola][0] == critico
    assert len(cola) == 2


def test_crear_app_sin_argumentos_usa_postgres(bd_limpia, monkeypatch):
    usar_base_de_pruebas(monkeypatch)
    with TestClient(crear_app()) as c:
        codigo = c.post("/reportes", json=CRITICO).json()["codigo"]
        c.post("/refugio/ingresos", json=INGRESO, headers=sesion(c, bd_limpia))
    assert RepositorioPostgres(bd_limpia).buscar(codigo) is not None
    assert RepositorioCuposPostgres.primer_refugio(bd_limpia).refugio().ocupados == 1


def test_ocupacion_sobrevive_a_un_reinicio_de_la_app(bd_limpia):
    """DT-05: antes la ocupación volvía a 0/40 al reiniciar."""
    c = cliente(bd_limpia)
    cabeceras = sesion(c, bd_limpia)
    assert c.post("/refugio/ingresos", json=INGRESO, headers=cabeceras).json() == {
        "ocupacion": "1/40"}
    # Otra instancia de la app: el token sigue sirviendo porque la cuenta está en la base.
    respuesta = cliente(bd_limpia).get("/refugio/ocupacion", headers=cabeceras)
    assert respuesta.json() == {"ocupacion": "1/40", "porcentaje": 2.5}


def test_refugio_lleno_rechaza_el_ingreso_con_409(bd_limpia):
    """RN-04 con la base: sin cupo el ingreso se rechaza y la ocupación no cambia."""
    preparar_refugio(bd_limpia, 40, 40)
    c = cliente(bd_limpia)
    cabeceras = sesion(c, bd_limpia)
    assert c.post("/refugio/ingresos", json=INGRESO, headers=cabeceras).status_code == 409
    assert c.get("/refugio/ocupacion", headers=cabeceras).json()["ocupacion"] == "40/40"


def test_el_arranque_falla_si_la_base_no_esta_migrada(motor_pruebas, monkeypatch):
    usar_base_de_pruebas(monkeypatch)
    revertir_migraciones(motor_pruebas, "base")
    try:
        with pytest.raises(BaseDeDatosDesactualizada, match="alembic upgrade head"):
            crear_app()
    finally:
        aplicar_migraciones(motor_pruebas)
