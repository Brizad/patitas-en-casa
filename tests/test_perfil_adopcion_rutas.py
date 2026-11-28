"""#508, parte 2: editar el perfil de adopción, la salud (solo veterinario) y la colección."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios
from tests.test_decision_adopcion import CLAVE, PERFIL, PUBLICACION, en_memoria, en_postgres, h

COORD, VET = "coord@patitas.co", "vet@patitas.co"
PERFIL_TOBY = {"estadisticas": {"energia": 5, "carino": 4, "juego": 5, "paciencia": 2},
               "habilidades": ["Rey del juego", "Bueno con niños"]}


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    s = ServicioUsuarios(usuarios)
    s.registrar(COORD, "Coord", Rol.COORDINADOR, CLAVE)
    s.registrar(VET, "Ana", Rol.VETERINARIO, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def publicar(c, nombre="Toby", **ficha):
    coord = h(c, COORD)
    c.post("/refugio/ingresos", json={"nombre": nombre, "especie": "perro",
                                      "estado_salud": "sano"}, headers=coord)
    animal_id = next(a["id"] for a in c.get("/refugio/animales", headers=coord).json()
                     if a["nombre"] == nombre)
    c.post(f"/refugio/animales/{animal_id}/publicacion", json={**PUBLICACION, **ficha},
           headers=coord)
    return animal_id


def test_sin_sesion_401_y_el_adoptante_no_edita(c):
    animal_id = publicar(c)
    perfil = f"/refugio/animales/{animal_id}/perfil-adopcion"
    salud = f"/refugio/animales/{animal_id}/salud-adopcion"
    assert c.get(perfil).status_code == 401
    assert c.put(perfil, json=PERFIL_TOBY).status_code == 401
    assert c.put(salud, json={"vacunas": True}).status_code == 401
    c.post("/adoptantes", json={"correo": "lau@correo.co", "nombre": "Lau", "contrasena": CLAVE,
                                "autoriza_datos": True})
    assert c.put(perfil, json=PERFIL_TOBY, headers=h(c, "lau@correo.co")).status_code == 403


@pytest.mark.parametrize("correo", [COORD, VET])
def test_coordinador_y_veterinario_editan_estadisticas_y_habilidades(c, correo):
    animal_id = publicar(c)
    r = c.put(f"/refugio/animales/{animal_id}/perfil-adopcion", json=PERFIL_TOBY,
              headers=h(c, correo))
    assert r.status_code == 200
    (toby,) = c.get("/adopciones/animales").json()
    assert toby["estadisticas"] == PERFIL_TOBY["estadisticas"]
    assert toby["tipo"] == "jugueton"  # calculado, no escrito
    assert toby["habilidades"] == ["Rey del juego", "Bueno con niños"]
    assert (toby["energia_nivel"], toby["calma"]) == (100, 40)


def test_si_el_nivel_no_cambia_se_queda_el_valor_fino_de_la_ficha(c):
    animal_id = publicar(c, carino=94, calma=45)  # 5 y 3
    datos = {"estadisticas": {"carino": 5, "paciencia": 3, "energia": 2}}
    c.put(f"/refugio/animales/{animal_id}/perfil-adopcion", json=datos, headers=h(c, VET))
    (toby,) = c.get("/adopciones/animales").json()
    assert (toby["carino"], toby["calma"], toby["energia_nivel"], toby["juego"]) == (94, 45, 40,
                                                                                    None)
    assert toby["tipo"] is None  # falta el juego: sin las 4 estadísticas no hay tipo


@pytest.mark.parametrize("malo", [
    {"estadisticas": {"energia": 0}}, {"estadisticas": {"energia": 6}},
    {"estadisticas": {}, "habilidades": ["Le gusta el queso"]}])
def test_valores_fuera_del_catalogo_o_de_1_a_5_se_rechazan(c, malo):
    animal_id = publicar(c)
    r = c.put(f"/refugio/animales/{animal_id}/perfil-adopcion", json=malo, headers=h(c, COORD))
    assert r.status_code == 422


def test_solo_el_veterinario_edita_la_salud(c):
    animal_id = publicar(c)
    ruta = f"/refugio/animales/{animal_id}/salud-adopcion"
    salud = {"vacunas": True, "esterilizado": False, "desparasitado": None}
    assert c.put(ruta, json=salud, headers=h(c, COORD)).status_code == 403
    assert c.put(ruta, json=salud, headers=h(c, VET)).status_code == 200
    (toby,) = c.get("/adopciones/animales").json()
    assert toby["salud"] == salud
    # El coordinador edita el perfil sin tocar la salud.
    c.put(f"/refugio/animales/{animal_id}/perfil-adopcion", json=PERFIL_TOBY, headers=h(c, COORD))
    assert c.get("/adopciones/animales").json()[0]["salud"] == salud


def test_lo_que_no_esta_publicado_o_no_es_del_refugio_no_se_edita(c):
    coord = h(c, COORD)
    c.post("/refugio/ingresos", json={"nombre": "Sin publicar", "especie": "gato",
                                      "estado_salud": "sana"}, headers=coord)
    animal_id = c.get("/refugio/animales", headers=coord).json()[0]["id"]
    assert c.get(f"/refugio/animales/{animal_id}/perfil-adopcion",
                 headers=coord).status_code == 404
    assert c.get("/refugio/animales/999/perfil-adopcion", headers=coord).status_code == 404


def test_el_perfil_se_lee_con_el_catalogo_de_habilidades(c):
    animal_id = publicar(c)
    r = c.get(f"/refugio/animales/{animal_id}/perfil-adopcion", headers=h(c, VET)).json()
    assert r["tipo"] is None and r["habilidades"] == []
    assert len(r["catalogo_habilidades"]) == 8


def _adoptar(c, animal_id, correo, registrar=True):
    if registrar:  # DT-09: 5 registros por IP cada 15 min
        c.post("/adoptantes", json={"correo": correo, "nombre": "X", "contrasena": CLAVE,
                                    "autoriza_datos": True})
        c.put("/adoptantes/yo/perfil", json=PERFIL, headers=h(c, correo))
    c.post("/adopciones/solicitudes", json={"animal_id": animal_id}, headers=h(c, correo))
    coord = h(c, COORD)
    solicitud = next(s["id"] for s in c.get("/refugio/solicitudes", headers=coord).json()
                     if s["animal_id"] == animal_id and s["estado"] == "pendiente")
    r = c.post(f"/refugio/solicitudes/{solicitud}/decision", json={"aprobar": True},
               headers=coord)
    assert r.status_code == 200
    return solicitud


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def cp(request):
    """Solo con el coordinador, en memoria y en PostgreSQL (la consulta de adoptadas)."""
    if request.param == "postgres":
        return en_postgres(request.getfixturevalue("bd_limpia"))
    return en_memoria()


def test_la_coleccion_cuenta_solo_adopciones_aprobadas_y_sin_datos_del_adoptante(cp):
    c = cp
    toby, luna, rocky = (publicar(c, n) for n in ("Toby", "Luna", "Rocky"))
    assert c.get("/adopciones/coleccion").json() == {"esperando": 3, "adoptados_total": 0,
                                                     "adoptados": []}
    _adoptar(c, toby, "lau@correo.co")
    solicitud_luna = _adoptar(c, luna, "ana@correo.co")
    c.post(f"/refugio/solicitudes/{solicitud_luna}/devolucion",  # RN-13: Luna volvió
           json={"texto": "La familia se mudó a otra ciudad"}, headers=h(c, COORD))
    col = c.get("/adopciones/coleccion").json()  # sin sesión
    assert (col["esperando"], col["adoptados_total"]) == (2, 1)
    (adoptado,) = col["adoptados"]
    assert adoptado["nombre"] == "Toby" and adoptado["adoptado_en"].endswith("+00:00")
    assert "correo" not in str(col) and "lau" not in str(col)
    assert rocky not in [a["animal_id"] for a in col["adoptados"]]


def test_la_coleccion_muestra_como_maximo_los_8_adoptados_mas_recientes(c):
    ids = [publicar(c, f"Animal {i}") for i in range(9)]
    for i, animal_id in enumerate(ids):
        _adoptar(c, animal_id, "lau@correo.co", registrar=i == 0)
    col = c.get("/adopciones/coleccion").json()
    assert col["adoptados_total"] == 9
    assert [a["nombre"] for a in col["adoptados"]] == [f"Animal {i}" for i in range(8, 0, -1)]
