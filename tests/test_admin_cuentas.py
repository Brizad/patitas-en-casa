"""Administración de cuentas (fase 1, #67): listar, crear, suspender y reactivar (RF-16)."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

# Valores falsos, solo para pruebas.
SECRETO = "secreto-de-pruebas-con-mas-de-32-caracteres"
CLAVE = "clave-de-prueba-larga"
NUEVA = {"correo": "Resc@Patitas.co", "nombre": "Rita", "rol": "rescatista",
         "contrasena": "otra-clave-de-prueba"}


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    servicio = ServicioUsuarios(usuarios)
    servicio.registrar("admin@patitas.co", "Admin", Rol.ADMINISTRADOR, CLAVE)
    servicio.registrar("vet@patitas.co", "Ana Vet", Rol.VETERINARIO, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=usuarios, emisor_tokens=EmisorTokens(SECRETO)))


def sesion(c, correo="admin@patitas.co", clave=CLAVE):
    respuesta = c.post("/auth/token", data={"username": correo, "password": clave})
    return {"Authorization": f"Bearer {respuesta.json()['access_token']}"}


@pytest.mark.parametrize("metodo, ruta", [
    ("get", "/admin/usuarios"), ("post", "/admin/usuarios"),
    ("put", "/admin/usuarios/vet@patitas.co/activo")])
def test_sin_sesion_responde_401_y_con_otro_rol_403(c, metodo, ruta):
    assert getattr(c, metodo)(ruta).status_code == 401
    assert getattr(c, metodo)(ruta, headers=sesion(c, "vet@patitas.co")).status_code == 403


def test_lista_las_cuentas_sin_el_hash_de_la_contrasena(c):
    cuentas = c.get("/admin/usuarios", headers=sesion(c)).json()
    assert [u["correo"] for u in cuentas] == ["admin@patitas.co", "vet@patitas.co"]
    assert cuentas[1] == {"correo": "vet@patitas.co", "nombre": "Ana Vet",
                          "rol": "veterinario", "activo": True}


def test_crea_una_cuenta_que_puede_iniciar_sesion(c):
    respuesta = c.post("/admin/usuarios", json=NUEVA, headers=sesion(c))
    assert respuesta.status_code == 201
    assert respuesta.json() == {"correo": "resc@patitas.co", "nombre": "Rita",
                                "rol": "rescatista", "activo": True}
    assert "contrasena" not in respuesta.text
    assert c.post("/auth/token", data={"username": "resc@patitas.co",
                                       "password": NUEVA["contrasena"]}).status_code == 200


def test_correo_repetido_responde_409_y_contrasena_corta_422(c):
    h = sesion(c)
    assert c.post("/admin/usuarios", json={**NUEVA, "correo": "vet@patitas.co"},
                  headers=h).status_code == 409
    corta = c.post("/admin/usuarios", json={**NUEVA, "contrasena": "corta"}, headers=h)
    assert corta.status_code == 422 and "12" in corta.json()["detail"]


def test_suspender_quita_el_acceso_de_inmediato_y_reactivar_lo_devuelve(c):
    h_vet = sesion(c, "vet@patitas.co")
    assert c.get("/cola", headers=h_vet).status_code == 200
    r = c.put("/admin/usuarios/vet@patitas.co/activo", json={"activo": False}, headers=sesion(c))
    assert r.status_code == 200 and r.json()["activo"] is False
    # El token emitido antes deja de servir: la cuenta se relee en cada petición.
    assert c.get("/cola", headers=h_vet).status_code == 401
    assert c.post("/auth/token", data={"username": "vet@patitas.co",
                                       "password": CLAVE}).status_code == 401
    c.put("/admin/usuarios/vet@patitas.co/activo", json={"activo": True}, headers=sesion(c))
    assert c.get("/cola", headers=sesion(c, "vet@patitas.co")).status_code == 200


def test_el_administrador_no_puede_suspenderse_a_si_mismo(c):
    """Evita quedarse sin ninguna cuenta de administración por un clic."""
    r = c.put("/admin/usuarios/admin@patitas.co/activo", json={"activo": False},
              headers=sesion(c))
    assert r.status_code == 409


def test_suspender_un_correo_inexistente_responde_404(c):
    r = c.put("/admin/usuarios/nadie@patitas.co/activo", json={"activo": False},
              headers=sesion(c))
    assert r.status_code == 404
