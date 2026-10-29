"""Datos de demostración (#109): se cargan solos, una sola vez, sin contraseñas en el código."""
import pytest
from fastapi.testclient import TestClient

from app.ajustes import cargar_ajustes_demo
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.demo import CUENTAS, correo
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

CLAVE_DEMO = "clave-de-demo-de-prueba"  # falsa, solo para pruebas


def cliente(**demo):
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Demo", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres"), **demo))


def h(c, usuario):
    t = c.post("/auth/token", data={"username": correo(usuario), "password": CLAVE_DEMO})
    return {"Authorization": f"Bearer {t.json()['access_token']}"}


def test_carga_una_cuenta_por_rol_y_datos_para_cada_pantalla():
    c = cliente(contrasena_demo=CLAVE_DEMO)
    roles = {c.get("/auth/yo", headers=h(c, u)).json()["rol"] for u, _, _ in CUENTAS}
    assert roles == {"administrador", "veterinario", "coordinador", "rescatista",
                     "adoptante", "alcaldia"}
    assert len(c.get("/cola", headers=h(c, "veterinaria")).json()) == 4
    assert len(c.get("/rescates/ofertas", headers=h(c, "rescatista")).json()) == 1
    assert len(c.get("/adopciones/animales").json()) == 3
    assert len(c.get("/refugio/animales", headers=h(c, "coordinador")).json()) == 4
    assert len(c.get("/refugio/animales", headers=h(c, "veterinaria")).json()) == 4
    recomendados = c.get("/adopciones/recomendaciones", headers=h(c, "adoptante")).json()
    assert recomendados and all(len(r["razones"]) == 3 for r in recomendados)


def test_sin_contrasena_no_carga_nada():
    c = cliente()
    r = c.post("/auth/token", data={"username": correo("veterinaria"), "password": CLAVE_DEMO})
    assert r.status_code == 401


def test_cargar_dos_veces_no_duplica(monkeypatch):
    c = cliente(contrasena_demo=CLAVE_DEMO)
    from app.demo import Dependencias, cargar_demo
    estado = c.app.state
    assert cargar_demo(Dependencias(estado.usuarios, *estado.demo_servicios), CLAVE_DEMO) is False


def test_los_ajustes_leen_la_contrasena_solo_del_entorno(monkeypatch):
    monkeypatch.delenv("PATITAS_DEMO_ACTIVA", raising=False)
    monkeypatch.delenv("PATITAS_DEMO_CONTRASENA", raising=False)
    assert cargar_ajustes_demo(archivo_env=None).contrasena_si_activa() is None
    monkeypatch.setenv("PATITAS_DEMO_ACTIVA", "true")
    monkeypatch.setenv("PATITAS_DEMO_CONTRASENA", CLAVE_DEMO)
    ajustes = cargar_ajustes_demo(archivo_env=None)
    assert ajustes.contrasena_si_activa() == CLAVE_DEMO
    assert CLAVE_DEMO not in repr(ajustes)


@pytest.mark.postgres
def test_carga_en_postgresql_como_en_render(bd_limpia):
    from app.cupos.repositorio_postgres import RepositorioCuposPostgres
    from app.reportes.repositorio_postgres import RepositorioPostgres
    from app.usuarios.repositorio_postgres import RepositorioUsuariosPostgres

    def app_postgres():
        return TestClient(crear_app(
            RepositorioPostgres(bd_limpia), RepositorioCuposPostgres.primer_refugio(bd_limpia),
            repositorio_usuarios=RepositorioUsuariosPostgres(bd_limpia),
            emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres"),
            contrasena_demo=CLAVE_DEMO))
    c = app_postgres()
    app_postgres()  # un reinicio de Render no duplica nada
    assert len(c.get("/adopciones/animales").json()) == 3
    assert len(c.get("/cola", headers=h(c, "veterinaria")).json()) == 4
