"""RF-27, RN-10 (#85): solicitar la adopción de un animal publicado."""
import pytest
from fastapi.testclient import TestClient

from app.adopciones.modelos import EstadoSolicitud, Solicitud
from app.adopciones.repositorio import RepositorioAdopcionesEnMemoria
from app.adopciones.repositorio_postgres import RepositorioAdopcionesPostgres
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
PERFIL = {"vivienda": "casa", "tiene_patio": True, "hay_ninos": False,
          "otros_animales": False, "horas_solo_al_dia": 4, "experiencia": True,
          "acepta_seguimiento": True}
PUBLICACION = {"descripcion": "Gata tranquila y cariñosa, le gusta dormir al sol",
               "tamano": "pequeno", "energia": "baja", "edad_meses": 24, "apto_ninos": True,
               "apto_otros_animales": False, "necesita_patio": False}


def h(c, correo):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


@pytest.fixture
def c():
    """Un refugio con Canela publicada y una adoptante con perfil completo."""
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("coord@patitas.co", "Coord", Rol.COORDINADOR, CLAVE)
    cliente = TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))
    coord = h(cliente, "coord@patitas.co")
    cliente.post("/refugio/ingresos", json={"nombre": "Canela", "especie": "gato",
                                            "estado_salud": "sana"}, headers=coord)
    cliente.post("/refugio/animales/1/publicacion", json=PUBLICACION, headers=coord)
    for correo in ("lau@correo.co", "sin@correo.co"):
        cliente.post("/adoptantes", json={"correo": correo, "nombre": "Laura",
                                          "contrasena": CLAVE, "autoriza_datos": True})
    cliente.put("/adoptantes/yo/perfil", json=PERFIL, headers=h(cliente, "lau@correo.co"))
    return cliente


def test_solicitar_y_ver_mis_solicitudes(c):
    lau = h(c, "lau@correo.co")
    r = c.post("/adopciones/solicitudes", json={"animal_id": 1, "mensaje": "Tengo patio"},
               headers=lau)
    assert r.status_code == 201 and r.json() == {"id": 1, "animal_id": 1, "estado": "pendiente"}
    assert [s["estado"] for s in c.get("/adopciones/solicitudes/mias", headers=lau).json()] \
        == ["pendiente"]
    repetida = c.post("/adopciones/solicitudes", json={"animal_id": 1}, headers=lau)
    assert repetida.status_code == 409


def test_rn10_sin_perfil_o_sin_aceptar_seguimiento_no_solicita(c):
    sin = h(c, "sin@correo.co")
    assert c.post("/adopciones/solicitudes", json={"animal_id": 1},
                  headers=sin).status_code == 422
    c.put("/adoptantes/yo/perfil", json={**PERFIL, "acepta_seguimiento": False}, headers=sin)
    r = c.post("/adopciones/solicitudes", json={"animal_id": 1}, headers=sin)
    assert r.status_code == 422 and "RN-10" in r.json()["detail"]


def test_animal_no_publicado_404_y_rol_equivocado_403(c):
    assert c.post("/adopciones/solicitudes", json={"animal_id": 99},
                  headers=h(c, "lau@correo.co")).status_code == 404
    assert c.post("/adopciones/solicitudes", json={"animal_id": 1},
                  headers=h(c, "coord@patitas.co")).status_code == 403
    assert c.post("/adopciones/solicitudes", json={"animal_id": 1}).status_code == 401


def test_el_coordinador_ve_la_solicitud_con_el_perfil(c):
    c.post("/adopciones/solicitudes", json={"animal_id": 1}, headers=h(c, "lau@correo.co"))
    assert c.get("/refugio/solicitudes", headers=h(c, "lau@correo.co")).status_code == 403
    (s,) = c.get("/refugio/solicitudes", headers=h(c, "coord@patitas.co")).json()
    assert (s["animal"], s["adoptante"], s["estado"]) == ("Canela", "lau@correo.co", "pendiente")
    assert s["perfil"]["horas_solo_al_dia"] == 4 and "correo" not in s["perfil"]


@pytest.mark.postgres
def test_contrato_postgres_una_pendiente_por_animal_y_adoptante(bd_limpia):
    from app.adopciones.modelos import Energia, Publicacion, Tamano
    from app.cupos.repositorio_postgres import RepositorioCuposPostgres
    from app.dominio.modelos import Animal, Especie
    from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres

    ServicioUsuarios(RepositorioUsuariosPostgres(bd_limpia)).registrar(
        "lau@correo.co", "Laura", Rol.ADOPTANTE, CLAVE)
    luna = Animal("Luna", Especie.PERRO, "sana")
    RepositorioCuposPostgres.primer_refugio(bd_limpia).ocupar_cupo(luna)
    repo = RepositorioAdopcionesPostgres(bd_limpia)
    repo.publicar(Publicacion(luna.id, "Perrita juguetona que ama correr", Tamano.MEDIANO,
                              Energia.ALTA, 12, True, True, True))
    _contrato(repo, luna.id)


def test_contrato_memoria():
    _contrato(RepositorioAdopcionesEnMemoria(), 1)


def _contrato(repo, animal_id):
    from datetime import UTC, datetime

    def nueva():
        return Solicitud(None, animal_id, "lau@correo.co", "", EstadoSolicitud.PENDIENTE,
                         datetime.now(UTC))
    primera = nueva()
    assert repo.crear_solicitud(primera) is True and primera.id is not None
    assert repo.crear_solicitud(nueva()) is False
    (guardada,) = repo.solicitudes()
    assert (guardada.id, guardada.estado) == (primera.id, EstadoSolicitud.PENDIENTE)
