"""Egresos que liberan cupo (RF-26, #75).

El egreso marca la ficha (fecha y motivo) y libera el cupo en una sola operación; un animal
egresa una sola vez. La ficha y su historial se conservan: el animal sale del refugio, no de
los registros.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Animal, Especie, MotivoEgreso, Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios
from tests.conftest import preparar_refugio

CLAVE = "clave-de-prueba-larga"  # falsa


def animal():
    return Animal(nombre="Luna", especie=Especie.PERRO, estado_salud="recuperada")


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")
        preparar_refugio(motor, 2, 0)
        return RepositorioCuposPostgres.primer_refugio(motor)
    return RepositorioCuposEnMemoria(Refugio("Demo", 2))


def test_egreso_libera_el_cupo_y_conserva_la_ficha(repositorio):
    luna = animal()
    repositorio.ocupar_cupo(luna)
    assert repositorio.refugio().texto_ocupacion() == "1/2"
    refugio = repositorio.egresar(luna.id, MotivoEgreso.ADOPCION)
    assert refugio.texto_ocupacion() == "0/2"
    ficha = repositorio.animal(luna.id)
    assert ficha.motivo_egreso == MotivoEgreso.ADOPCION and ficha.egresado_en is not None


def test_un_animal_egresa_una_sola_vez(repositorio):
    luna = animal()
    repositorio.ocupar_cupo(luna)
    repositorio.ocupar_cupo(animal())
    repositorio.egresar(luna.id, MotivoEgreso.TRASLADO)
    assert repositorio.egresar(luna.id, MotivoEgreso.TRASLADO) is None
    assert repositorio.refugio().texto_ocupacion() == "1/2"  # no liberó dos veces
    assert repositorio.egresar(9999, MotivoEgreso.TRASLADO) is None


def test_lleno_egreso_y_vuelve_a_haber_cupo(repositorio):
    for _ in range(2):
        repositorio.ocupar_cupo(animal())
    assert repositorio.ocupar_cupo(animal()) is None  # RN-04
    primero = repositorio.animales()[0]
    repositorio.egresar(primero.id, MotivoEgreso.DEVUELTO)
    assert repositorio.ocupar_cupo(animal()) is not None


def test_api_egreso_solo_del_coordinador():
    usuarios = RepositorioUsuariosEnMemoria()
    s = ServicioUsuarios(usuarios)
    s.registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE)
    s.registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    c = TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))

    def h(correo):
        t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
        return {"Authorization": f"Bearer {t['access_token']}"}

    coord = h("coord@patitas.co")
    c.post("/refugio/ingresos", json={"nombre": "Canela", "especie": "gato",
                                      "estado_salud": "sana"}, headers=coord)
    (ficha,) = c.get("/refugio/animales", headers=coord).json()
    ruta = f"/refugio/animales/{ficha['id']}/egreso"
    assert c.post(ruta, json={"motivo": "adopcion"}).status_code == 401
    assert c.post(ruta, json={"motivo": "adopcion"}, headers=h("vet@patitas.co")).status_code \
        == 403
    r = c.post(ruta, json={"motivo": "adopcion"}, headers=coord)
    assert r.status_code == 200 and r.json() == {"ocupacion": "0/40"}
    assert c.post(ruta, json={"motivo": "adopcion"}, headers=coord).status_code == 409
    detalle = c.get(f"/refugio/animales/{ficha['id']}", headers=coord).json()
    assert detalle["motivo_egreso"] == "adopcion" and detalle["egresado_en"].endswith("+00:00")
