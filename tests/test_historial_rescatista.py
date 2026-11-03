"""Historial del rescatista (Mis rescates): lo que aceptó, del más reciente al más viejo."""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio, Rol
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from app.usuarios.servicio import ServicioUsuarios

CLAVE = "clave-de-prueba-larga"  # falsa
CRITICO = "Perro atropellado en la avenida, está sangrando mucho"
CUENTAS = [("vet@patitas.co", Rol.VETERINARIO), ("coord@patitas.co", Rol.COORDINADOR),
           ("ana@rescate.co", Rol.RESCATISTA), ("luis@rescate.co", Rol.RESCATISTA)]


@pytest.fixture
def c():
    usuarios = RepositorioUsuariosEnMemoria()
    for correo, rol in CUENTAS:
        ServicioUsuarios(usuarios).registrar(correo, correo.split("@")[0], rol, CLAVE)
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=usuarios,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def sesion(c, correo):
    token = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {token['access_token']}"}


def confirmado(c):
    codigo = c.post("/reportes", json={"descripcion": CRITICO,
                                       "direccion": "Calle 8 con Av. 4"}).json()["codigo"]
    c.post(f"/reportes/{codigo}/confirmacion", json={}, headers=sesion(c, "vet@patitas.co"))
    return codigo


def test_historial_sin_sesion_da_401(c):
    assert c.get("/rescates/historial").status_code == 401


@pytest.mark.parametrize("correo", ["vet@patitas.co", "coord@patitas.co"])
def test_historial_de_otro_rol_da_403(c, correo):
    assert c.get("/rescates/historial", headers=sesion(c, correo)).status_code == 403


def test_historial_muestra_mis_rescates_con_llegada_y_resultado(c):
    ana = sesion(c, "ana@rescate.co")
    c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=ana)
    primero, segundo = confirmado(c), confirmado(c)
    c.post(f"/rescates/{primero}/aceptar", headers=ana)
    c.post(f"/rescates/{primero}/llegue", headers=ana)
    c.post(f"/rescates/{primero}/resultado", json={"resultado": "trasladado"}, headers=ana)
    c.post(f"/rescates/{segundo}/aceptar", headers=ana)
    historial = c.get("/rescates/historial", headers=ana).json()
    assert [h["codigo"] for h in historial] == [segundo, primero]
    en_camino, atendido = historial
    assert (en_camino["estado"], en_camino["llego"], en_camino["resultado"]) == (
        "en_camino", False, None)
    assert (atendido["estado"], atendido["llego"], atendido["resultado"]) == (
        "atendido", True, "trasladado")
    assert atendido["aceptado_en"].endswith("+00:00")
    # Nada del reporte: ni descripción ni dirección.
    assert set(en_camino) == {"codigo", "aceptado_en", "llego", "resultado", "estado",
                              "actualizado_en"}


def test_historial_no_incluye_rescates_de_otro_ni_liberados(c):
    ana, luis = sesion(c, "ana@rescate.co"), sesion(c, "luis@rescate.co")
    for cabeceras in (ana, luis):
        c.put("/rescatistas/yo/disponibilidad", json={"disponible": True}, headers=cabeceras)
    codigo = confirmado(c)
    c.post(f"/rescates/{codigo}/aceptar", headers=ana)
    c.post(f"/rescates/{codigo}/liberar", headers=ana)
    assert c.get("/rescates/historial", headers=ana).json() == []
    c.post(f"/rescates/{codigo}/aceptar", headers=luis)
    assert [h["codigo"] for h in c.get("/rescates/historial", headers=luis).json()] == [codigo]
    assert c.get("/rescates/historial", headers=ana).json() == []
