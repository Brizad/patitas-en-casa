"""RF-25 (#85): el coordinador publica un animal de su refugio; el catálogo es público."""
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.adopciones.modelos import Energia, Publicacion, Tamano
from app.adopciones.repositorio import RepositorioAdopcionesEnMemoria
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Animal, Especie, Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
DATOS = {"descripcion": "Gata tranquila y cariñosa, le gusta dormir al sol",
         "tamano": "pequeno", "energia": "baja", "edad_meses": 24, "apto_ninos": True,
         "apto_otros_animales": False, "necesita_patio": False}


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    s = ServicioUsuarios(usuarios)
    s.registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    s.registrar("vet@patitas.co", "Ana", Rol.VETERINARIO, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo="coord@patitas.co"):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def ingresar(c, h, nombre="Canela"):
    c.post("/refugio/ingresos", json={"nombre": nombre, "especie": "gato",
                                      "estado_salud": "sana"}, headers=h)
    return next(a["id"] for a in c.get("/refugio/animales", headers=h).json()
                if a["nombre"] == nombre)


def test_publicar_y_aparecer_en_el_catalogo_publico(c):
    h = sesion(c)
    animal_id = ingresar(c, h)
    r = c.post(f"/refugio/animales/{animal_id}/publicacion", json=DATOS, headers=h)
    assert r.status_code == 201
    (publicado,) = c.get("/adopciones/animales").json()  # sin sesión
    assert (publicado["nombre"], publicado["especie"], publicado["estado"]) == (
        "Canela", "gato", "disponible")
    assert publicado["publicado_en"].endswith("+00:00")


def test_reglas_de_publicacion(c):
    h = sesion(c)
    animal_id = ingresar(c, h)
    ruta = f"/refugio/animales/{animal_id}/publicacion"
    assert c.post(ruta, json=DATOS).status_code == 401
    assert c.post(ruta, json=DATOS, headers=sesion(c, "vet@patitas.co")).status_code == 403
    assert c.post(ruta, json={**DATOS, "descripcion": "corta"}, headers=h).status_code == 422
    assert c.post("/refugio/animales/999/publicacion", json=DATOS, headers=h).status_code == 404
    c.post(ruta, json=DATOS, headers=h)
    assert c.post(ruta, json=DATOS, headers=h).status_code == 409  # una vez


def test_un_animal_que_egreso_no_se_publica(c):
    h = sesion(c)
    animal_id = ingresar(c, h)
    c.post(f"/refugio/animales/{animal_id}/egreso", json={"motivo": "traslado"}, headers=h)
    r = c.post(f"/refugio/animales/{animal_id}/publicacion", json=DATOS, headers=h)
    assert r.status_code == 409


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def repos(request):
    if request.param == "postgres":
        motor = request.getfixturevalue("bd_limpia")
        return RepositorioCuposPostgres.primer_refugio(motor), RepositorioAdopcionesPostgres(motor)
    return RepositorioCuposEnMemoria(Refugio("Demo", 40)), RepositorioAdopcionesEnMemoria()


def test_contrato_una_publicacion_por_animal(repos):
    cupos, adopciones = repos
    luna = Animal("Luna", Especie.PERRO, "sana")
    cupos.ocupar_cupo(luna)
    publicacion = Publicacion(luna.id, "Perrita juguetona que ama correr", Tamano.MEDIANO,
                              Energia.ALTA, 12, True, True, True, nombre="Luna", especie="perro")
    assert adopciones.publicar(publicacion) is True
    assert adopciones.publicar(publicacion) is False
    (disponible,) = adopciones.disponibles()
    assert (disponible.animal_id, disponible.nombre, disponible.tamano) == (
        luna.id, "Luna", Tamano.MEDIANO)
    assert adopciones.publicacion(luna.id).energia == Energia.ALTA
    assert adopciones.publicacion(9999) is None


# ---------- #422: ficha «Elige a tu compañero» (opcional, solo para mostrar) ----------

FICHA = {"carino": 95, "energia_nivel": 92, "juego": 90, "calma": 38,
         "etiquetas": ["Juguetón", " Guardián ", "Vacunado"], "peso_kg": 8, "peso_adulto_kg": 35.5}


def test_la_ficha_se_publica_y_sale_en_el_catalogo(c):
    h = sesion(c)
    animal_id = ingresar(c, h)
    r = c.post(f"/refugio/animales/{animal_id}/publicacion", json={**DATOS, **FICHA}, headers=h)
    assert r.status_code == 201
    (publicado,) = c.get("/adopciones/animales").json()
    assert {k: publicado[k] for k in FICHA} == {**FICHA, "etiquetas": ["Juguetón", "Guardián",
                                                                       "Vacunado"]}


def test_sin_ficha_los_campos_quedan_vacios(c):
    h = sesion(c)
    c.post(f"/refugio/animales/{ingresar(c, h)}/publicacion", json=DATOS, headers=h)
    (publicado,) = c.get("/adopciones/animales").json()
    assert [publicado[k] for k in FICHA] == [None, None, None, None, [], None, None]


@pytest.mark.parametrize("malo", [{"carino": 101}, {"calma": -1}, {"juego": "mucho"},
                                  {"etiquetas": ["a", "b", "c", "d"]}, {"etiquetas": ["x" * 21]},
                                  {"etiquetas": ["  "]}, {"peso_kg": 0}, {"peso_adulto_kg": 151}])
def test_la_ficha_se_valida(c, malo):
    h = sesion(c)
    r = c.post(f"/refugio/animales/{ingresar(c, h)}/publicacion", json={**DATOS, **malo},
               headers=h)
    assert r.status_code == 422


def test_editar_la_publicacion(c):
    h = sesion(c)
    animal_id = ingresar(c, h)
    ruta = f"/refugio/animales/{animal_id}/publicacion"
    assert c.put(ruta, json=DATOS, headers=h).status_code == 404  # aún no publicado
    c.post(ruta, json=DATOS, headers=h)
    assert c.put(ruta, json=DATOS).status_code == 401
    assert c.put(ruta, json=DATOS, headers=sesion(c, "vet@patitas.co")).status_code == 403
    assert c.put(ruta, json={**DATOS, "carino": 200}, headers=h).status_code == 422
    r = c.put(ruta, json={**DATOS, **FICHA, "energia": "alta"}, headers=h)
    assert r.status_code == 200
    assert (r.json()["carino"], r.json()["energia"], r.json()["nombre"]) == (95, "alta", "Canela")
    (publicado,) = c.get("/adopciones/animales").json()
    assert (publicado["energia"], publicado["peso_adulto_kg"]) == ("alta", 35.5)
    assert c.put("/refugio/animales/999/publicacion", json=DATOS, headers=h).status_code == 404


def test_contrato_ficha_y_edicion(repos):
    cupos, adopciones = repos
    toby = Animal("Toby", Especie.PERRO, "sano")
    cupos.ocupar_cupo(toby)
    base = Publicacion(toby.id, "Perro juguetón que ama correr", Tamano.GRANDE, Energia.ALTA, 3,
                       True, True, True, nombre="Toby", especie="perro")
    adopciones.publicar(replace(base, carino=95, etiquetas=["Juguetón"], peso_kg=8.5))
    guardada = adopciones.publicacion(toby.id)
    assert (guardada.carino, guardada.juego, guardada.etiquetas, guardada.peso_kg) == (
        95, None, ["Juguetón"], 8.5)
    assert adopciones.actualizar_publicacion(replace(
        base, juego=90, etiquetas=[], peso_adulto_kg=35.25, descripcion="Cambió la descripción"))
    (editada,) = adopciones.disponibles()
    assert (editada.carino, editada.juego, editada.etiquetas, editada.peso_adulto_kg,
            editada.descripcion, editada.nombre) == (
        None, 90, [], 35.25, "Cambió la descripción", "Toby")
    assert not adopciones.actualizar_publicacion(replace(base, animal_id=9999))
