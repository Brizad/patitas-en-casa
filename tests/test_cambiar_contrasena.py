"""ASVS 2.1.5 y 2.1.6: cada persona puede cambiar su contraseña, y para hacerlo debe dar la
actual. Antes la contraseña la ponía el administrador al crear la cuenta y nadie podía
cambiarla: quien la creó la seguía conociendo."""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.api.main import crear_app
from app.bitacora.repositorio import RepositorioBitacoraEnMemoria
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"  # falso
VIEJA = "clave-que-puso-el-admin"  # falsa
NUEVA = "mi-frase-secreta-nueva"  # falsa
CORREO = "vet@patitas.co"


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    servicio = ServicioUsuarios(usuarios)
    servicio.registrar(CORREO, "Ana", Rol.VETERINARIO, VIEJA)
    servicio.registrar("adoptante@patitas.co", "Luz", Rol.ADOPTANTE, VIEJA)
    bitacora = RepositorioBitacoraEnMemoria()
    cliente = TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO),
        repositorio_bitacora=bitacora))
    cliente.usuarios, cliente.bitacora = usuarios, bitacora
    return cliente


def entrar(c, clave, correo=CORREO):
    return c.post("/auth/token", data={"username": correo, "password": clave})


def sesion(c, clave=VIEJA, correo=CORREO):
    return {"Authorization": f"Bearer {entrar(c, clave, correo).json()['access_token']}"}


def cambiar(c, actual, nueva, encabezados):
    return c.post("/auth/contrasena", json={"actual": actual, "nueva": nueva},
                  headers=encabezados)


def test_cambiar_la_contrasena_exige_sesion(c):
    assert cambiar(c, VIEJA, NUEVA, {}).status_code == 401


def test_con_la_actual_correcta_la_nueva_sirve_y_la_vieja_deja_de_servir(c):
    respuesta = cambiar(c, VIEJA, NUEVA, sesion(c))
    assert respuesta.status_code == 200 and respuesta.json() == {"cambiada": True}
    assert entrar(c, VIEJA).status_code == 401
    assert entrar(c, NUEVA).status_code == 200


def test_sin_la_contrasena_actual_no_se_cambia(c):
    """Un token robado (o una sesión abierta en un computador ajeno) no alcanza."""
    respuesta = cambiar(c, "no-es-la-actual-123", NUEVA, sesion(c))
    assert respuesta.status_code == 403
    assert "actual no es correcta" in respuesta.json()["detail"]
    assert entrar(c, VIEJA).status_code == 200


@pytest.mark.parametrize(("nueva", "mensaje"), [
    ("corta", "entre 12 y 128"),
    (VIEJA, "distinta de la actual"),
])
def test_la_nueva_cumple_la_politica_y_no_repite_la_actual(c, nueva, mensaje):
    respuesta = cambiar(c, VIEJA, nueva, sesion(c))
    assert respuesta.status_code == 422 and mensaje in respuesta.json()["detail"]
    assert entrar(c, VIEJA).status_code == 200


def test_la_contrasena_se_guarda_solo_como_hash_argon2id(c):
    cambiar(c, VIEJA, NUEVA, sesion(c))
    guardado = c.usuarios.buscar_por_correo(CORREO).hash_contrasena
    assert guardado.startswith("$argon2id$") and NUEVA not in guardado


def test_adivinar_la_actual_se_frena_como_el_inicio_de_sesion(c):
    """DT-06: los fallos cuentan para el mismo límite del correo; al llegar, 429."""
    encabezados = sesion(c)
    for _ in range(config.INTENTOS_MAXIMOS):
        assert cambiar(c, "adivinando-la-clave", NUEVA, encabezados).status_code == 403
    bloqueado = cambiar(c, VIEJA, NUEVA, encabezados)
    assert bloqueado.status_code == 429 and "Retry-After" in bloqueado.headers
    assert entrar(c, VIEJA).status_code == 429  # el mismo candado del inicio de sesión


def test_cualquier_rol_cambia_la_suya_y_solo_la_suya(c):
    encabezados = sesion(c, correo="adoptante@patitas.co")
    assert cambiar(c, VIEJA, NUEVA, encabezados).status_code == 200
    assert entrar(c, NUEVA, "adoptante@patitas.co").status_code == 200
    assert entrar(c, VIEJA).status_code == 200  # la de la veterinaria no cambió


def test_el_cambio_queda_en_la_bitacora_sin_ninguna_contrasena(c):
    cambiar(c, VIEJA, NUEVA, sesion(c))
    eventos = c.bitacora.de_actor(CORREO, "POST /auth/contrasena")
    assert len(eventos) == 1 and eventos[0].estado_http == 200
    assert VIEJA not in repr(eventos) and NUEVA not in repr(eventos)
