"""Ficha clínica con historial (RF-06, RF-24, #75).

Cada animal ingresado tiene su ficha y un historial de notas (observación, tratamiento,
vacuna, procedimiento) que solo crece: no hay forma de editar ni borrar una nota, igual que
la bitácora de triaje. Las notas las escribe el veterinario; cada persona ve los animales
de su refugio.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.fichas import NotaInvalida, ServicioFichas
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Animal, Especie, Refugio, Rol, TipoNota, Usuario
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

VET = Usuario("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, hash_contrasena="x")
CLAVE = "clave-de-prueba-larga"  # falsa


def animal(nombre="Luna"):
    return Animal(nombre=nombre, especie=Especie.PERRO, estado_salud="herida en la pata")


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repositorio(request):
    if request.param == "postgres":
        return RepositorioCuposPostgres.primer_refugio(request.getfixturevalue("bd_limpia"))
    return RepositorioCuposEnMemoria(Refugio("Demo", 40))


def test_el_ingreso_crea_la_ficha_con_id(repositorio):
    luna = animal()
    repositorio.ocupar_cupo(luna)
    assert luna.id is not None
    (ficha,) = repositorio.animales()
    assert (ficha.id, ficha.nombre, ficha.estado_salud) == (luna.id, "Luna", "herida en la pata")
    assert ficha.ingresado_en is not None
    assert repositorio.animal(luna.id).nombre == "Luna"
    assert repositorio.animal(9999) is None


def test_las_notas_se_acumulan_en_orden(repositorio):
    luna = animal()
    repositorio.ocupar_cupo(luna)
    fichas = ServicioFichas(repositorio)
    fichas.agregar_nota(luna.id, VET, TipoNota.TRATAMIENTO, "Amoxicilina cada 12 horas")
    fichas.agregar_nota(luna.id, VET, TipoNota.VACUNA, "Primera dosis de rabia")
    historial = repositorio.historial(luna.id)
    assert [(n.tipo, n.texto, n.autor) for n in historial] == [
        (TipoNota.TRATAMIENTO, "Amoxicilina cada 12 horas", "vet@patitas.co"),
        (TipoNota.VACUNA, "Primera dosis de rabia", "vet@patitas.co")]


@pytest.mark.parametrize("texto", ["", "   ", "....."])
def test_nota_vacia_o_sin_letras_se_rechaza(repositorio, texto):
    luna = animal()
    repositorio.ocupar_cupo(luna)
    with pytest.raises(NotaInvalida):
        ServicioFichas(repositorio).agregar_nota(luna.id, VET, TipoNota.OBSERVACION, texto)
    assert repositorio.historial(luna.id) == []


@pytest.mark.postgres
def test_no_se_ve_un_animal_de_otro_refugio(bd_limpia):
    otro = RepositorioRefugiosPostgres(bd_limpia).crear("Huellitas", 10)
    luna = animal()
    RepositorioCuposPostgres(bd_limpia, otro.id).ocupar_cupo(luna)
    primero = RepositorioCuposPostgres.primer_refugio(bd_limpia)
    assert primero.animal(luna.id) is None and primero.animales() == []
    with pytest.raises(LookupError):
        ServicioFichas(primero).agregar_nota(luna.id, VET, TipoNota.OBSERVACION, "Come bien")


# --- API ---------------------------------------------------------------------

def cliente():
    usuarios = RepositorioUsuariosEnMemoria()
    s = ServicioUsuarios(usuarios)
    s.registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    s.registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_api_ficha_e_historial():
    c = cliente()
    vet, coord = sesion(c, "vet@patitas.co"), sesion(c, "coord@patitas.co")
    assert c.get("/refugio/animales").status_code == 401
    c.post("/refugio/ingresos", json={"nombre": "Canela", "especie": "gato",
                                      "estado_salud": "desnutrición leve"}, headers=coord)
    (ficha,) = c.get("/refugio/animales", headers=vet).json()
    assert ficha["nombre"] == "Canela" and ficha["ingresado_en"].endswith("+00:00")
    ruta = f"/refugio/animales/{ficha['id']}"
    nota = {"tipo": "tratamiento", "texto": "Dieta blanda por tres días"}
    assert c.post(f"{ruta}/historial", json=nota, headers=coord).status_code == 403
    assert c.post(f"{ruta}/historial", json=nota, headers=vet).status_code == 201
    detalle = c.get(ruta, headers=coord).json()
    assert detalle["nombre"] == "Canela"
    assert [(n["tipo"], n["texto"], n["autor"]) for n in detalle["historial"]] == [
        ("tratamiento", "Dieta blanda por tres días", "vet@patitas.co")]
    assert c.get("/refugio/animales/9999", headers=vet).status_code == 404
    assert c.post("/refugio/animales/9999/historial", json=nota, headers=vet).status_code == 404
