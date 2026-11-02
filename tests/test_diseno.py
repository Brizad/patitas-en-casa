"""Sistema de diseño único (#164): una hoja de estilo compartida por inicio, PWA y panel."""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria

CSS = Path(__file__).resolve().parents[1] / "app" / "diseno" / "sistema.css"


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def test_la_hoja_se_sirve_como_css_sin_sesion(c):
    r = c.get("/diseno/sistema.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")


def test_define_los_componentes_del_sistema():
    css = CSS.read_text(encoding="utf-8")
    for clase in ("ds-btn", "ds-btn--pri", "ds-tarjeta", "ds-tabla", "ds-insignia",
                  "ds-insignia--critica", "ds-insignia--alta", "ds-insignia--media",
                  "ds-insignia--baja", "ds-vacio", "ds-msg--error", "ds-msg--ok"):
        assert f".{clase}" in css, clase


def test_tiene_modo_oscuro_y_sin_recursos_externos():
    css = CSS.read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in css
    assert not re.search(r"https?://|@import", css)  # la CSP solo admite el propio servidor


def test_las_casillas_se_alinean_con_su_texto():
    css = CSS.read_text(encoding="utf-8")
    assert 'label:has(> input[type="checkbox"])' in css
