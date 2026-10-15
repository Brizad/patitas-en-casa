"""Inicio de sesión con JWT (DT-02, parte 2)."""
import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from app.ajustes import ConfiguracionIncompleta, cargar_ajustes_seguridad
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol, Usuario
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens, TokenInvalido
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

# Valores falsos, solo para pruebas.
SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"
CLAVE = "clave-de-prueba-larga"
VET = Usuario("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, hash_contrasena="x")


def emisor(minutos=30, reloj=None):
    return EmisorTokens(SECRETO, minutos=minutos, reloj=reloj)


def app_con_usuario():
    usuarios = RepositorioUsuariosEnMemoria()
    ServicioUsuarios(usuarios).registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    app = crear_app(RepositorioEnMemoria(),
                    RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
                    repositorio_usuarios=usuarios, emisor_tokens=emisor())
    return TestClient(app), usuarios


def iniciar_sesion(c, correo="vet@patitas.co", contrasena=CLAVE):
    return c.post("/auth/token", data={"username": correo, "password": contrasena})


# --- Tokens ---------------------------------------------------------------

def test_token_emitido_se_valida_con_correo_y_rol():
    sesion = emisor().validar(emisor().emitir(VET))
    assert (sesion.correo, sesion.rol) == ("vet@patitas.co", Rol.VETERINARIO)


def test_token_vencido_se_rechaza():
    hace_una_hora = datetime.now(UTC) - timedelta(hours=1)
    token = emisor(minutos=30, reloj=lambda: hace_una_hora).emitir(VET)
    with pytest.raises(TokenInvalido):
        emisor().validar(token)


def test_token_firmado_con_otra_clave_se_rechaza():
    token = EmisorTokens("otra-clave-distinta-tambien-de-32-caracteres").emitir(VET)
    with pytest.raises(TokenInvalido):
        emisor().validar(token)


def test_token_manipulado_se_rechaza():
    """Cambiar el rol dentro del token rompe la firma."""
    cabecera, cuerpo, firma = emisor().emitir(VET).split(".")
    datos = json.loads(base64.urlsafe_b64decode(cuerpo + "=="))
    datos["rol"] = "coordinador"
    falso = base64.urlsafe_b64encode(json.dumps(datos).encode()).rstrip(b"=").decode()
    with pytest.raises(TokenInvalido):
        emisor().validar(f"{cabecera}.{falso}.{firma}")


def test_token_sin_firma_alg_none_se_rechaza():
    ahora = datetime.now(UTC)
    token = jwt.encode({"sub": VET.correo, "rol": "coordinador", "iss": "patitas-en-casa",
                        "iat": ahora, "exp": ahora + timedelta(minutes=5)},
                       key=None, algorithm="none")
    with pytest.raises(TokenInvalido):
        emisor().validar(token)


@pytest.mark.parametrize("token", ["", "basura", "a.b.c"])
def test_texto_que_no_es_token_se_rechaza(token):
    with pytest.raises(TokenInvalido):
        emisor().validar(token)


def test_clave_de_firma_corta_se_rechaza():
    with pytest.raises(ValueError, match="32"):
        EmisorTokens("corta")


# --- Configuración --------------------------------------------------------

def test_sin_clave_jwt_da_un_error_claro(monkeypatch):
    monkeypatch.delenv("PATITAS_JWT_SECRETO", raising=False)
    with pytest.raises(ConfiguracionIncompleta, match="PATITAS_JWT_SECRETO"):
        cargar_ajustes_seguridad(archivo_env=None)


def test_clave_jwt_corta_da_un_error_claro(monkeypatch):
    monkeypatch.setenv("PATITAS_JWT_SECRETO", "corta")
    with pytest.raises(ConfiguracionIncompleta, match="PATITAS_JWT_SECRETO"):
        cargar_ajustes_seguridad(archivo_env=None)


def test_ajustes_de_seguridad_no_imprimen_la_clave(monkeypatch):
    monkeypatch.setenv("PATITAS_JWT_SECRETO", SECRETO)
    monkeypatch.setenv("PATITAS_JWT_MINUTOS", "15")
    ajustes = cargar_ajustes_seguridad(archivo_env=None)
    assert ajustes.jwt_minutos == 15
    assert SECRETO not in repr(ajustes)


# --- API --------------------------------------------------------------------

def test_inicio_de_sesion_correcto_devuelve_un_token_bearer():
    c, _ = app_con_usuario()
    respuesta = iniciar_sesion(c, correo="VET@patitas.co")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["token_type"] == "bearer"
    assert cuerpo["expira_en"] == 30 * 60
    assert emisor().validar(cuerpo["access_token"]).correo == "vet@patitas.co"


def test_credenciales_incorrectas_dan_401_con_el_mismo_mensaje():
    """No se revela si el correo existe."""
    c, _ = app_con_usuario()
    mala_clave = iniciar_sesion(c, contrasena="clave-equivocada-123")
    sin_cuenta = iniciar_sesion(c, correo="nadie@patitas.co")
    assert mala_clave.status_code == sin_cuenta.status_code == 401
    assert mala_clave.json() == sin_cuenta.json()
    assert mala_clave.headers["WWW-Authenticate"] == "Bearer"


def test_yo_devuelve_la_cuenta_del_token():
    c, _ = app_con_usuario()
    token = iniciar_sesion(c).json()["access_token"]
    respuesta = c.get("/auth/yo", headers={"Authorization": f"Bearer {token}"})
    assert respuesta.json() == {"correo": "vet@patitas.co", "nombre": "Ana Vet",
                                "rol": "veterinario"}


@pytest.mark.parametrize("cabeceras", [{}, {"Authorization": "Bearer basura"},
                                       {"Authorization": "Basic dmV0OmNsYXZl"}])
def test_yo_sin_token_valido_da_401(cabeceras):
    c, _ = app_con_usuario()
    assert c.get("/auth/yo", headers=cabeceras).status_code == 401


def test_cuenta_desactivada_pierde_el_acceso_aunque_tenga_token():
    c, usuarios = app_con_usuario()
    token = iniciar_sesion(c).json()["access_token"]
    usuarios.buscar_por_correo("vet@patitas.co").activo = False
    assert c.get("/auth/yo", headers={"Authorization": f"Bearer {token}"}).status_code == 401
