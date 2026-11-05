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
    assert "@media (min-width: 720px)" in css  # una columna en celular, varias en pantalla ancha
    # El modo oscuro viene del sistema de diseño compartido (#164).
    assert "prefers-color-scheme: dark" in (CARPETA.parent / "diseno" / "sistema.css").read_text(
        encoding="utf-8")


def test_usa_el_sistema_de_diseno(c):
    html = c.get("/").text
    assert re.search(r"<body[^>]*class=\"ds\"", html)
    assert html.index("/diseno/sistema.css") < html.index("/inicio/inicio.css")
    assert c.get("/diseno/sistema.css").status_code == 200


# --- Rediseño (#293, parte 2): sistema visual de DESIGN.md con fuentes locales. ---

def _css():
    return (CARPETA / "inicio.css").read_text(encoding="utf-8")


def _contraste(a: str, b: str) -> float:
    def luz(h):
        r, g, b_ = (int(h.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4  # noqa: E731
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b_)
    claro, oscuro = sorted((luz(a), luz(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def test_usa_las_fuentes_locales(c):
    html = c.get("/").text
    assert html.index("/diseno/fuentes.css") < html.index("/inicio/inicio.css")
    precargas = re.findall(r'<link rel="preload"[^>]*href="([^"]+)"', html)
    assert precargas and all(p.startswith("/diseno/fuentes/") for p in precargas)
    css = _css()
    assert "'EB Garamond'" in css and "'Figtree'" in css
    assert c.get(precargas[0]).headers["content-type"] == "font/woff2"


def test_el_titulo_no_pasa_de_44_px_en_celular():
    m = re.search(r"\.portada h1 \{[^}]*font-size: clamp\(([\d.]+)rem, ([\d.]+)rem \+ ([\d.]+)vw, "
                  r"([\d.]+)rem\)", _css())
    assert m, "el título de la portada usa clamp(Arem, Brem + Cvw, Drem)"
    minimo, base, vw, maximo = map(float, m.groups())
    en_360 = min(max(minimo * 16, base * 16 + vw * 3.6), maximo * 16)
    assert en_360 <= 44 and maximo * 16 >= 64  # grande en escritorio, contenido en celular


def test_botones_con_borde_de_2px_y_sin_sombras_ni_degradados():
    css = _css()
    assert re.search(r"\.boton \{[^}]*border: 2px solid", css)
    assert "gradient" not in css and not re.search(r"box-shadow: (?!none)", css)


def test_colores_con_contraste_aa_en_claro_y_oscuro():
    css = _css()
    claro, oscuro = css.split("prefers-color-scheme: dark", 1)
    tokens = dict(re.findall(r"--(\w[\w-]*): (#[0-9a-fA-F]{6})", claro))
    assert tokens["suave"].lower() != "#8a8a80"  # el gris de DESIGN.md no llega a 4,5:1
    for texto, fondo in (("tinta", "crema"), ("suave", "crema"), ("crema", "tinta"),
                         ("tinta", "lavanda"), ("crema", "bosque")):
        assert _contraste(tokens[texto], tokens[fondo]) >= 4.5, (texto, fondo)
    noche = {**tokens, **dict(re.findall(r"--(\w[\w-]*): (#[0-9a-fA-F]{6})", oscuro))}
    for texto, fondo in (("texto", "lienzo"), ("suave", "lienzo"), ("texto", "camara")):
        assert _contraste(noche[texto], noche[fondo]) >= 4.5, ("oscuro", texto, fondo)
