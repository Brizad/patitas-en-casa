"""El panel del personal (#64) se sirve en /panel/ solo si está compilado, con CSP estricta."""
from fastapi.testclient import TestClient

import app.api.main as principal
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria


def cliente():
    return TestClient(principal.crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def test_panel_compilado_se_sirve_con_politica_de_seguridad(tmp_path, monkeypatch):
    (tmp_path / "index.html").write_text("<!doctype html><div id='raiz'></div>")
    monkeypatch.setattr(principal, "CARPETA_PANEL", tmp_path)
    respuesta = cliente().get("/panel/")
    assert respuesta.status_code == 200 and "raiz" in respuesta.text
    assert "script-src 'self'" in respuesta.headers["Content-Security-Policy"]


def test_sin_compilar_el_panel_no_existe(tmp_path, monkeypatch):
    monkeypatch.setattr(principal, "CARPETA_PANEL", tmp_path / "no-existe")
    assert cliente().get("/panel/").status_code == 404
