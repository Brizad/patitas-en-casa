"""Ingresos y ocupación del refugio de cada persona (#75, sigue a RF-14 de la fase 1).

Quien está vinculado a un refugio registra ingresos y ve la ocupación de ESE refugio; sin
vínculo se usa el primer refugio, como antes (compatibilidad con las cuentas existentes).
"""
import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio_postgres import RepositorioCuposPostgres
from app.dominio.modelos import Rol
from app.refugios.repositorio_postgres import RepositorioRefugiosPostgres
from app.reportes.repositorio_postgres import RepositorioPostgres
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres
from app.usuarios.servicio import ServicioUsuarios

pytestmark = pytest.mark.postgres
CLAVE = "clave-de-prueba-larga"  # falsa
INGRESO = {"nombre": "Canela", "especie": "gato", "estado_salud": "desnutrición leve"}


def sesion(c, correo):
    t = c.post("/auth/token", data={"username": correo, "password": CLAVE}).json()
    return {"Authorization": f"Bearer {t['access_token']}"}


def test_cada_coordinador_usa_los_cupos_de_su_refugio(bd_limpia):
    usuarios = RepositorioUsuariosPostgres(bd_limpia)
    servicio = ServicioUsuarios(usuarios)
    servicio.registrar("norte@patitas.co", "Norte", Rol.COORDINADOR, CLAVE)
    servicio.registrar("sin@patitas.co", "Sin refugio", Rol.COORDINADOR, CLAVE)
    huellitas = RepositorioRefugiosPostgres(bd_limpia).crear("Huellitas", 25)
    usuarios.vincular_refugio("norte@patitas.co", huellitas.id)
    c = TestClient(crear_app(RepositorioPostgres(bd_limpia),
                             RepositorioCuposPostgres.primer_refugio(bd_limpia),
                             repositorio_usuarios=usuarios,
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-car")))
    norte, sin = sesion(c, "norte@patitas.co"), sesion(c, "sin@patitas.co")
    assert c.post("/refugio/ingresos", json=INGRESO, headers=norte).json() == {
        "ocupacion": "1/25"}
    assert c.get("/refugio/ocupacion", headers=norte).json()["ocupacion"] == "1/25"
    # El primer refugio (demo, 40 cupos) no cambió; quien no tiene vínculo lo sigue usando.
    assert c.get("/refugio/ocupacion", headers=sin).json()["ocupacion"] == "0/40"
    assert c.post("/refugio/ingresos", json=INGRESO, headers=sin).json() == {
        "ocupacion": "1/40"}
