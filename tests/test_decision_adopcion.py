"""RF-27 (decidir), RN-05, RN-11 y RF-10 (#85).

Aprobar: sin restricciones duras (RN-05); rechaza las demás pendientes del animal y una sola
aprobada por animal (RN-11); el animal egresa por adopción y libera el cupo; se programan
los seguimientos a 30, 90 y 180 días (RF-10). Rechazar exige una razón sin relleno.
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Refugio, Rol
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.repositorio import RepositorioEnMemoria
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
PERFIL = {"vivienda": "casa", "tiene_patio": True, "hay_ninos": False,
          "otros_animales": False, "horas_solo_al_dia": 4, "experiencia": True,
          "acepta_seguimiento": True}
PUBLICACION = {"descripcion": "Gata tranquila y cariñosa, le gusta dormir al sol",
               "tamano": "pequeno", "energia": "baja", "edad_meses": 24, "apto_ninos": False,
               "apto_otros_animales": True, "necesita_patio": False}
RAZON = "Prefiere esperar a mudarse a una casa más grande"


def h(c, correo):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def preparar(c):
    """Canela publicada (no apta con niños) y dos adoptantes: Lau sin niños, Ana con niños."""
    coord = h(c, "coord@patitas.co")
    c.post("/refugio/ingresos", json={"nombre": "Canela", "especie": "gato",
                                      "estado_salud": "sana"}, headers=coord)
    animal_id = c.get("/refugio/animales", headers=coord).json()[0]["id"]
    c.post(f"/refugio/animales/{animal_id}/publicacion", json=PUBLICACION, headers=coord)
    for correo, ninos in (("lau@correo.co", False), ("ana@correo.co", True)):
        c.post("/adoptantes", json={"correo": correo, "nombre": "X", "contrasena": CLAVE,
                                    "autoriza_datos": True})
        c.put("/adoptantes/yo/perfil", json={**PERFIL, "hay_ninos": ninos}, headers=h(c, correo))
        c.post("/adopciones/solicitudes", json={"animal_id": animal_id}, headers=h(c, correo))
    ids = {s["adoptante"]: s["id"] for s in c.get("/refugio/solicitudes", headers=coord).json()}
    return coord, animal_id, ids


def en_memoria():
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def en_postgres(motor):
    usuarios = RepositorioUsuariosPostgres(motor)
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    return TestClient(crear_app(
        RepositorioPostgres(motor), RepositorioCuposPostgres.primer_refugio(motor),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


@pytest.fixture(params=["memoria", pytest.param("postgres", marks=pytest.mark.postgres)])
def c(request):
    if request.param == "postgres":
        return en_postgres(request.getfixturevalue("bd_limpia"))
    return en_memoria()


def test_rn05_restriccion_dura_impide_aprobar(c):
    coord, _, ids = preparar(c)
    r = c.post(f"/refugio/solicitudes/{ids['ana@correo.co']}/decision", json={"aprobar": True},
               headers=coord)
    assert r.status_code == 409 and "niños" in r.json()["detail"]


def test_aprobar_egresa_rechaza_las_otras_y_programa_seguimientos(c):
    coord, animal_id, ids = preparar(c)
    r = c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/decision", json={"aprobar": True},
               headers=coord)
    assert r.status_code == 200 and r.json()["estado"] == "aprobada"
    assert [s["dia"] for s in r.json()["seguimientos"]] == [30, 90, 180]
    estados = {s["adoptante"]: s["estado"]
               for s in c.get("/refugio/solicitudes", headers=coord).json()}
    assert estados == {"lau@correo.co": "aprobada", "ana@correo.co": "rechazada"}
    assert c.get("/adopciones/animales").json() == []  # ya no está disponible
    ficha = c.get(f"/refugio/animales/{animal_id}", headers=coord).json()
    assert ficha["motivo_egreso"] == "adopcion"
    assert c.get("/refugio/ocupacion", headers=coord).json()["ocupacion"].startswith("0/")
    again = c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/decision",
                   json={"aprobar": True}, headers=coord)
    assert again.status_code == 409


def test_rechazar_exige_razon_sin_relleno(c):
    coord, _, ids = preparar(c)
    ruta = f"/refugio/solicitudes/{ids['lau@correo.co']}/decision"
    assert c.post(ruta, json={"aprobar": False}, headers=coord).status_code == 422
    assert c.post(ruta, json={"aprobar": False, "razon": ".........."},
                  headers=coord).status_code == 422
    r = c.post(ruta, json={"aprobar": False, "razon": RAZON}, headers=coord)
    assert r.status_code == 200 and r.json()["razon"] == RAZON
    mias = c.get("/adopciones/solicitudes/mias", headers=h(c, "lau@correo.co")).json()
    assert mias[0]["estado"] == "rechazada"


def test_decidir_es_solo_del_coordinador_de_ese_refugio(c):
    coord, _, ids = preparar(c)
    ruta = f"/refugio/solicitudes/{ids['lau@correo.co']}/decision"
    assert c.post(ruta, json={"aprobar": True}).status_code == 401
    assert c.post(ruta, json={"aprobar": True},
                  headers=h(c, "lau@correo.co")).status_code == 403
    assert c.post("/refugio/solicitudes/999/decision", json={"aprobar": True},
                  headers=coord).status_code == 404


@pytest.mark.postgres
def test_coordinador_de_otro_refugio_no_ve_ni_decide(bd_limpia):
    c = en_postgres(bd_limpia)
    _, _, ids = preparar(c)
    otro = RepositorioRefugiosPostgres(bd_limpia).crear("Huellitas", 10)
    usuarios = RepositorioUsuariosPostgres(bd_limpia)
    ServicioUsuarios(usuarios).registrar("norte@patitas.co", "Norte", Rol.COORDINADOR, CLAVE)
    usuarios.vincular_refugio("norte@patitas.co", otro.id)
    norte = h(c, "norte@patitas.co")
    assert c.get("/refugio/solicitudes", headers=norte).json() == []
    assert c.post(f"/refugio/solicitudes/{ids['lau@correo.co']}/decision",
                  json={"aprobar": True}, headers=norte).status_code == 404
