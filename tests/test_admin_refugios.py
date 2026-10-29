"""Administración de refugios y vínculo del personal (fase 1, #67, RF-14)."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.refugios.repositorio import RepositorioRefugiosEnMemoria
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios

# Valores falsos, solo para pruebas.
SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"
CLAVE = "clave-de-prueba-larga"


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    servicio = ServicioUsuarios(usuarios)
    servicio.registrar("admin@patitas.co", "Admin", Rol.ADMINISTRADOR, CLAVE)
    servicio.registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO)))


def sesion(c, correo="admin@patitas.co"):
    respuesta = c.post("/auth/token", data={"username": correo, "password": CLAVE})
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/admin/refugios"), ("post", "/admin/refugios"),
    ("put", "/admin/usuarios/coord@patitas.co/refugio")])
def test_sin_sesion_responde_401_y_con_otro_rol_403(c, metodo, ruta):
    assert getattr(c, metodo)(ruta).status_code == 401
    assert getattr(c, metodo)(ruta, headers=sesion(c, "coord@patitas.co")).status_code == 403


def test_lista_el_refugio_demo_y_registra_otro(c):
    h = sesion(c)
    assert c.get("/admin/refugios", headers=h).json() == [
        {"id": 1, "nombre": "Refugio demo", "capacidad": 40, "ocupados": 0}]
    nuevo = c.post("/admin/refugios", json={"nombre": " Huellitas ", "capacidad": 25},
                   headers=h)
    assert nuevo.status_code == 201
    assert nuevo.json() == {"id": 2, "nombre": "Huellitas", "capacidad": 25, "ocupados": 0}
    assert len(c.get("/admin/refugios", headers=h).json()) == 2


@pytest.mark.parametrize("datos", [{"nombre": "", "capacidad": 10},
                                   {"nombre": "Sin cupos", "capacidad": 0}])
def test_refugio_sin_nombre_o_sin_capacidad_responde_422(c, datos):
    assert c.post("/admin/refugios", json=datos, headers=sesion(c)).status_code == 422


def test_vincular_personal_a_un_refugio(c):
    h = sesion(c)
    r = c.put("/admin/usuarios/coord@patitas.co/refugio", json={"refugio_id": 1}, headers=h)
    assert r.status_code == 200
    cuentas = {u["correo"]: u for u in c.get("/admin/usuarios", headers=h).json()}
    assert cuentas["coord@patitas.co"]["refugio_id"] == 1
    c.put("/admin/usuarios/coord@patitas.co/refugio", json={"refugio_id": None}, headers=h)
    cuentas = {u["correo"]: u for u in c.get("/admin/usuarios", headers=h).json()}
    assert cuentas["coord@patitas.co"]["refugio_id"] is None


def test_vincular_a_un_refugio_o_cuenta_inexistente_responde_404(c):
    h = sesion(c)
    assert c.put("/admin/usuarios/coord@patitas.co/refugio", json={"refugio_id": 99},
                 headers=h).status_code == 404
    assert c.put("/admin/usuarios/nadie@patitas.co/refugio", json={"refugio_id": 1},
                 headers=h).status_code == 404


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repos(request):
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")  # trae el refugio demo con id 1
        return RepositorioRefugiosPostgres(motor), RepositorioUsuariosPostgres(motor)
    return (RepositorioRefugiosEnMemoria([Refugio("Refugio demo Cúcuta", 40, id=1)]),
            RepositorioUsuariosEnMemoria())


def test_contrato_crear_listar_y_vincular(repos):
    refugios, usuarios = repos
    nuevo = refugios.crear("Huellitas", 25)
    assert (nuevo.id, nuevo.nombre, nuevo.capacidad, nuevo.ocupados) == (2, "Huellitas", 25, 0)
    assert [r.id for r in refugios.todos()] == [1, 2]
    assert refugios.existe(2) and not refugios.existe(99)
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    assert usuarios.vincular_refugio("coord@patitas.co", 2) is True
    assert usuarios.buscar_por_correo("coord@patitas.co").refugio_id == 2
    assert usuarios.vincular_refugio("nadie@patitas.co", 2) is False
