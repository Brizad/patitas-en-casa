"""DT-09 (#149): registro público de adoptantes con límite por IP y sin revelar correos."""
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.config import REGISTROS_MAXIMOS_POR_IP
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.intentos import (
    LimiteIntentos,
    RepositorioIntentosEnMemoria,
    clave_ip,
    clave_registro,
)
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

CLAVE = "clave-de-adoptante-larga"


def cuenta(correo="lau@correo.co", contrasena=CLAVE):
    return {"correo": correo, "nombre": "Laura", "contrasena": contrasena,
            "autoriza_datos": True}


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def entra(c, correo, contrasena):
    return c.post("/auth/token", data={"username": correo, "password": contrasena}).status_code


def test_correo_nuevo_y_correo_repetido_responden_exactamente_igual(c):
    nuevo = c.post("/adoptantes", json=cuenta())
    repetido = c.post("/adoptantes", json=cuenta(contrasena="otra-clave-muy-larga"))
    assert nuevo.status_code == repetido.status_code == 201
    assert nuevo.json() == repetido.json()


def test_el_registro_repetido_no_cambia_la_cuenta_existente(c):
    c.post("/adoptantes", json=cuenta())
    c.post("/adoptantes", json=cuenta(contrasena="otra-clave-muy-larga"))
    assert entra(c, "lau@correo.co", CLAVE) == 200
    assert entra(c, "lau@correo.co", "otra-clave-muy-larga") == 401


def test_demasiados_registros_desde_la_misma_ip_responden_429(c):
    for i in range(REGISTROS_MAXIMOS_POR_IP):
        assert c.post("/adoptantes", json=cuenta(f"a{i}@correo.co")).status_code == 201
    bloqueado = c.post("/adoptantes", json=cuenta("otro@correo.co"))
    assert bloqueado.status_code == 429
    assert int(bloqueado.headers["Retry-After"]) > 0
    assert entra(c, "otro@correo.co", CLAVE) == 401  # no se creó


def test_los_intentos_fallidos_tambien_cuentan(c):
    for _ in range(REGISTROS_MAXIMOS_POR_IP):
        c.post("/adoptantes", json=cuenta(contrasena="corta"))
    assert c.post("/adoptantes", json=cuenta()).status_code == 429


def test_el_limite_de_registro_es_aparte_del_de_inicio_de_sesion():
    ahora = datetime(2026, 10, 29, tzinfo=UTC)
    limite = LimiteIntentos(RepositorioIntentosEnMemoria(), reloj=lambda: ahora)
    for _ in range(REGISTROS_MAXIMOS_POR_IP):
        limite.registrar_fallo([clave_registro("1.2.3.4")])
    assert limite.segundos_de_bloqueo([clave_registro("1.2.3.4")]) > 0
    assert limite.segundos_de_bloqueo([clave_ip("1.2.3.4")]) == 0
    assert limite.segundos_de_bloqueo([clave_registro("5.6.7.8")]) == 0


def test_el_bloqueo_del_registro_termina_con_la_ventana():
    momento = [datetime(2026, 10, 29, tzinfo=UTC)]
    limite = LimiteIntentos(RepositorioIntentosEnMemoria(), reloj=lambda: momento[0])
    for _ in range(REGISTROS_MAXIMOS_POR_IP):
        limite.registrar_fallo([clave_registro("1.2.3.4")])
    momento[0] += timedelta(minutes=16)
    assert limite.segundos_de_bloqueo([clave_registro("1.2.3.4")]) == 0
