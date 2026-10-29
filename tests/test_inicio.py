"""Página de inicio pública en la raíz del sitio (#145)."""
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

CARPETA = Path(__file__).resolve().parents[1] / "app" / "inicio"


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def test_la_raiz_muestra_la_pagina_de_inicio(c):
    respuesta = c.get("/", follow_redirects=False)
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    html = respuesta.text
    assert '<html lang="es">' in html and 'name="viewport"' in html
    assert "Cúcuta" in html


def test_tiene_los_tres_botones_grandes(c):
    html = c.get("/").text
    assert re.search(r'href="/app/#reportar"[^>]*>Reportar emergencia<', html)
    assert re.search(r'href="/panel/#registro"[^>]*>Adoptar<', html)
    assert re.search(r'href="/panel/"[^>]*>Entrar como personal<', html)


def test_explica_el_flujo_los_roles_y_la_tecnologia(c):
    html = c.get("/").text
    for paso in ("Reporte", "IA de texto y video", "Veterinario", "Rescate", "Refugio",
                 "Adopción"):
        assert paso in html
    for rol in ("Ciudadano", "Veterinario", "Rescatista", "Coordinador", "Adoptante",
                "Administrador", "Alcaldía"):
        assert f"<dt>{rol}</dt>" in html
    assert "FastAPI" in html and "PostgreSQL" in html


def test_usa_la_misma_csp_estricta_y_su_estilo_se_sirve(c):
    raiz = c.get("/")
    assert "script-src 'self'" in raiz.headers["content-security-policy"]
    estilo = c.get("/inicio/inicio.css")
    assert estilo.status_code == 200 and "text/css" in estilo.headers["content-type"]
    assert "content-security-policy" in estilo.headers


def test_sin_javascript_ni_recursos_externos():
    html = (CARPETA / "index.html").read_text(encoding="utf-8")
    assert "<script" not in html and not re.search(r"<[^>]*\son\w+=", html)
    recursos = re.findall(r'(?:src|href)="([^"]+)"', html)
    externos = [r for r in recursos if r.startswith("http") and "github.com" not in r]
    assert externos == []  # solo el enlace al repositorio sale del sitio


def test_se_ve_bien_en_celular():
    css = (CARPETA / "inicio.css").read_text(encoding="utf-8")
    assert "min-height: 56px" in css  # botones grandes (objetivo ≥ 24 px, WCAG 2.5.8)
    assert "@media (min-width: 640px)" in css  # una columna en celular, tres en pantalla ancha
    assert "prefers-color-scheme: dark" in css
