"""#486: cada inicio de sesión deja entrar solo a su rol. «Entrar como adoptante» manda
portal=adoptante y «¿Trabajas en el refugio?» manda portal=personal; si la contraseña es correcta
pero el rol no es de ese portal, el servidor responde 403 sin token."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa, solo para pruebas
PERSONAL = [Rol.VETERINARIO, Rol.COORDINADOR, Rol.RESCATISTA, Rol.ADMINISTRADOR, Rol.ALCALDIA]
GENERICO = "Correo o contraseña incorrectos."


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    servicio = ServicioUsuarios(usuarios)
    for rol in [*PERSONAL, Rol.ADOPTANTE]:
        servicio.registrar(f"{rol.value}@patitas.co", rol.value, rol, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def entrar(c, rol, portal, contrasena=CLAVE):
    datos = {"username": f"{rol.value}@patitas.co", "password": contrasena}
    if portal:
        datos["portal"] = portal
    return c.post("/auth/token", data=datos)


def test_adoptante_entra_por_su_portal(c):
    respuesta = entrar(c, Rol.ADOPTANTE, "adoptante")
    assert respuesta.status_code == 200
    assert respuesta.json()["access_token"]


@pytest.mark.parametrize("rol", PERSONAL)
def test_personal_entra_por_su_portal(c, rol):
    assert entrar(c, rol, "personal").status_code == 200


@pytest.mark.parametrize("rol", PERSONAL)
def test_personal_en_el_portal_de_adoptante_recibe_403_sin_token(c, rol):
    respuesta = entrar(c, rol, "adoptante")
    assert respuesta.status_code == 403
    assert "access_token" not in respuesta.json()
    assert "set-cookie" not in respuesta.headers
    assert respuesta.json()["detail"] == (
        "Esta cuenta es del personal del refugio. Entra por «¿Trabajas en el refugio?».")


def test_adoptante_en_el_portal_del_personal_recibe_403_sin_token(c):
    respuesta = entrar(c, Rol.ADOPTANTE, "personal")
    assert respuesta.status_code == 403
    assert "access_token" not in respuesta.json()
    assert "set-cookie" not in respuesta.headers
    assert respuesta.json()["detail"] == "Esta cuenta es de adoptante. Entra por «Adoptar»."


@pytest.mark.parametrize(("rol", "portal"), [(Rol.ADOPTANTE, "personal"),
                                             (Rol.VETERINARIO, "adoptante")])
def test_contrasena_mala_da_el_mensaje_generico_aunque_el_portal_no_sea_el_suyo(c, rol, portal):
    """No se revela de qué tipo es la cuenta (ni si existe) sin la contraseña correcta."""
    respuesta = entrar(c, rol, portal, contrasena="otra-clave-incorrecta")
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == GENERICO
    assert entrar(c, Rol.ADOPTANTE, "adoptante", "x" * 14).json()["detail"] == GENERICO


def test_correo_inexistente_da_el_mismo_mensaje_generico(c):
    respuesta = c.post("/auth/token", data={"username": "nadie@patitas.co", "password": CLAVE,
                                            "portal": "adoptante"})
    assert (respuesta.status_code, respuesta.json()["detail"]) == (401, GENERICO)


def test_un_portal_desconocido_se_rechaza(c):
    assert entrar(c, Rol.ADOPTANTE, "otro").status_code == 422


def test_el_rechazo_por_portal_no_cuenta_como_inicio_de_sesion(c):
    """Sin token no hay sesión: el historial de acceso (RF-16) no registra el intento."""
    entrar(c, Rol.ADOPTANTE, "personal")
    admin = entrar(c, Rol.ADMINISTRADOR, "personal").json()["access_token"]
    accesos = c.get("/admin/usuarios/adoptante@patitas.co/accesos",
                    headers={"Authorization": f"Bearer {admin}"})
    assert accesos.json() == []


def test_sesion_de_adoptante_no_abre_rutas_del_personal(c):
    token = entrar(c, Rol.ADOPTANTE, "adoptante").json()["access_token"]
    cabecera = {"Authorization": f"Bearer {token}"}
    for ruta in ["/cola", "/refugio/ocupacion", "/admin/usuarios", "/indicadores",
                 "/rescates/ofertas"]:
        assert c.get(ruta, headers=cabecera).status_code == 403, ruta


@pytest.mark.parametrize("rol", PERSONAL)
def test_sesion_del_personal_no_actua_como_adoptante(c, rol):
    token = entrar(c, rol, "personal").json()["access_token"]
    cabecera = {"Authorization": f"Bearer {token}"}
    assert c.get("/adoptantes/yo/perfil", headers=cabecera).status_code == 403
    assert c.get("/adopciones/recomendaciones", headers=cabecera).status_code == 403
