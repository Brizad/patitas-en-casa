"""Fuentes locales del sistema visual (#293): EB Garamond y Figtree (SIL OFL 1.1) servidas por
el propio servidor, sin Google Fonts ni otro origen (la CSP solo admite 'self')."""
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

DISENO = Path(__file__).resolve().parents[1] / "app" / "diseno"
ARCHIVOS = ("eb-garamond-latin-400-normal.woff2", "figtree-latin-wght-normal.woff2")


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


@pytest.mark.parametrize("archivo", ARCHIVOS)
def test_cada_fuente_se_sirve_desde_el_propio_servidor(c, archivo):
    r = c.get(f"/diseno/fuentes/{archivo}")
    assert r.status_code == 200
    assert r.headers["content-type"] == "font/woff2"
    assert r.content[:4] == b"wOF2"  # un woff2 de verdad, no una página de error
    assert "default-src 'self'" in r.headers["content-security-policy"]


def test_la_hoja_de_fuentes_declara_las_dos_familias_sin_otros_origenes(c):
    r = c.get("/diseno/fuentes.css")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/css")
    css = r.text
    assert css.count("@font-face") == 2
    assert "font-family: 'EB Garamond'" in css and "font-family: 'Figtree'" in css
    assert css.count("font-display: swap") == 2  # el texto se ve aunque la fuente tarde
    urls = re.findall(r"url\(([^)]+)\)", css)
    assert sorted(urls) == sorted(f"/diseno/fuentes/{a}" for a in ARCHIVOS)
    assert not re.search(r"https?://|@import", css)


@pytest.mark.parametrize("familia, licencia", [("EB Garamond", "OFL-EB-Garamond.txt"),
                                               ("Figtree", "OFL-Figtree.txt")])
def test_cada_fuente_va_con_su_licencia(familia, licencia):
    texto = (DISENO / "fuentes" / licencia).read_text(encoding="utf-8")
    assert f"The {familia} Project Authors" in texto
    assert "SIL OPEN FONT LICENSE Version 1.1" in texto
