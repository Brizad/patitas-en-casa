"""RF-08 (#85): el adoptante crea su cuenta, autoriza el uso de sus datos y llena su perfil."""
import pytest
from fastapi.testclient import TestClient

from app.adopciones.modelos import PerfilAdoptante, Vivienda
from app.adopciones.repositorio import RepositorioAdopcionesEnMemoria
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.cifrado import Cifrador
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
CUENTA = {"correo": "Lau@Correo.co", "nombre": "Laura", "contrasena": CLAVE,
          "autoriza_datos": True}
PERFIL = {"vivienda": "casa", "tiene_patio": True, "hay_ninos": True, "otros_animales": False,
          "horas_solo_al_dia": 4, "experiencia": True, "acepta_seguimiento": True}


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo="lau@correo.co"):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_registro_publico_crea_una_cuenta_de_adoptante(c):
    r = c.post("/adoptantes", json=CUENTA)
    assert r.status_code == 201
    assert r.json()["correo"] == "lau@correo.co" and r.json()["rol"] == "adoptante"
    assert c.get("/auth/yo", headers=sesion(c)).json()["rol"] == "adoptante"


def test_sin_autorizar_el_tratamiento_de_datos_no_hay_cuenta(c):
    """Ley 1581 de 2012: el tratamiento de datos personales necesita autorización."""
    r = c.post("/adoptantes", json={**CUENTA, "autoriza_datos": False})
    assert r.status_code == 422
    assert c.post("/auth/token", data={"username": "lau@correo.co",
                                       "password": CLAVE}).status_code == 401


def test_contrasena_corta_422(c):
    assert c.post("/adoptantes", json={**CUENTA, "correo": "otro@correo.co",
                                       "contrasena": "corta"}).status_code == 422


def test_el_adoptante_llena_y_actualiza_su_perfil(c):
    c.post("/adoptantes", json=CUENTA)
    h = sesion(c)
    assert c.get("/adoptantes/yo/perfil", headers=h).status_code == 404
    assert c.put("/adoptantes/yo/perfil", json=PERFIL, headers=h).status_code == 200
    c.put("/adoptantes/yo/perfil", json={**PERFIL, "horas_solo_al_dia": 2}, headers=h)
    perfil = c.get("/adoptantes/yo/perfil", headers=h).json()
    assert perfil["horas_solo_al_dia"] == 2 and perfil["vivienda"] == "casa"


def test_el_perfil_es_solo_del_adoptante(c):
    assert c.get("/adoptantes/yo/perfil").status_code == 401
    assert c.put("/adoptantes/yo/perfil", json=PERFIL,
                 headers=sesion(c, "vet@patitas.co")).status_code == 403


def test_perfil_con_horas_imposibles_responde_422(c):
    c.post("/adoptantes", json=CUENTA)
    r = c.put("/adoptantes/yo/perfil", json={**PERFIL, "horas_solo_al_dia": 25},
              headers=sesion(c))
    assert r.status_code == 422


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres),
                        pytest.param("postgres_cifrado", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param.startswith("postgres"):
        motor = request.getfixturevalue("bd_limpia")
        ServicioUsuarios(RepositorioUsuariosPostgres(motor)).registrar(
            "lau@correo.co", "Laura", Rol.ADOPTANTE, CLAVE)
        # #149 (RNF-08): el mismo contrato con el perfil cifrado.
        cifrador = (Cifrador("clave-de-datos-falsa-con-mas-de-32-caracteres")
                    if request.param == "postgres_cifrado" else None)
        return RepositorioAdopcionesPostgres(motor, cifrador)
    return RepositorioAdopcionesEnMemoria()


def test_contrato_guardar_y_reemplazar_el_perfil(repositorio):
    perfil = PerfilAdoptante("lau@correo.co", Vivienda.APARTAMENTO, False, False, True, 8,
                             False, True)
    repositorio.guardar_perfil(perfil)
    repositorio.guardar_perfil(PerfilAdoptante("lau@correo.co", Vivienda.CASA, True, False,
                                               True, 8, False, True))
    guardado = repositorio.perfil("lau@correo.co")
    assert (guardado.vivienda, guardado.tiene_patio) == (Vivienda.CASA, True)
    assert repositorio.perfil("nadie@correo.co") is None
