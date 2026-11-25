"""Página de inicio pública en la raíz del sitio (#145; arreglos, parte A: hero editorial y
bloques de color tipo collage)."""
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

RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "app" / "inicio"


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def _html():
    return (CARPETA / "index.html").read_text(encoding="utf-8")


def _css():
    return (CARPETA / "inicio.css").read_text(encoding="utf-8")


def _js():
    return (CARPETA / "inicio.js").read_text(encoding="utf-8")


def test_la_raiz_muestra_la_pagina_de_inicio(c):
    respuesta = c.get("/", follow_redirects=False)
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    html = respuesta.text
    assert '<html lang="es">' in html and 'name="viewport"' in html and "Cúcuta" in html


def test_hero_editorial_con_volver_en_naranja_italica():
    html, css = _html(), _css()
    assert re.search(r'<h1 id="titulo" class="serif">[^<]*<em>volver</em>', html)
    assert re.search(r"\.hero h1 em \{[^}]*font-style: italic; color: var\(--naranja-texto\)", css)
    assert 'data-animal="Max"' in html and 'data-animal="Pecas"' in html
    assert "Un veterinario revisa" in html and 'class="cifras-hero"' in html


def test_secciones_en_orden_y_colores_del_collage():
    html, css = _html(), _css()
    marcas = ['class="hero', 'class="cinta"', 'class="collage', 'id="problema"', 'class="adopcion"',
              'class="ayuda', 'id="roles"', 'class="final', 'class="carril"', 'class="pie"']
    posiciones = [html.index(m) for m in marcas]
    assert posiciones == sorted(posiciones)
    colores = ("#1F2A6B", "#0E5E6F", "#4F5BD5", "#FFE135", "#5B2A86", "#1F4FBF", "#12235E",
               "#F2603A")
    for color in colores:
        assert color in css, color
    assert "Ayúdalos, ayúdanos" in html and "¿Eres rescatista?" in html and "Cómo funciona" in html


def test_sin_rastro_de_huellas_ni_pausa_ni_nota_de_cifras():
    html, css = _html(), _css()
    assert 'class="rastro"' not in html and "huella-perro" not in html
    assert "Pausar animaciones" not in html and "pausa" not in css
    assert "Cifras en vivo" not in html and "aún sin dato" not in html
    assert "@media (prefers-reduced-motion: reduce)" in css  # el movimiento se apaga por CSS


def test_las_cifras_nunca_se_inventan():
    html, js = _html(), _js()
    valores = re.findall(r'data-cifra="(\w+)">([^<]*)<', html)
    assert {k for k, _ in valores} == {"reportes", "rescatados", "en_adopcion"}
    assert all(v == "—" for _, v in valores)  # sin dato, «—»
    assert '"/indicadores/publicos"' in js and "Number.isInteger(valor)" in js
    assert 'ponerCifra("en_adopcion", lista.length)' in js


def test_fotos_reales_por_nombre_y_nunca_rotas():
    html, js = _html(), _js()
    for nombre in ("Max", "Pecas", "Pinina", "Cascabel", "Winny", "Tigre", "Copo", "Nube", "Luna"):
        assert f'data-animal="{nombre}"' in html, nombre
    assert '"/adopciones/animales"' in js and "innerHTML" not in js
    assert 'img.addEventListener("error", () => img.remove())' in js


def test_los_enlaces_llevan_a_las_partes_reales(c):
    html = c.get("/").text
    assert html.count('href="/app/#reportar"') >= 4
    assert 'href="/app/#estado"' in html and 'href="/panel/#adoptar"' in html
    assert 'href="/panel/#personal"' in html and 'href="/docs"' in html
    assert '<button class="boton boton--blanco" type="button" id="compartir"' in html


def test_misma_csp_estricta_sin_scripts_ni_estilos_en_linea(c):
    raiz = c.get("/")
    assert "script-src 'self'" in raiz.headers["content-security-policy"]
    html = _html()
    assert re.findall(r"<script[^>]*>", html) == ['<script src="/inicio/inicio.js" defer>']
    assert not re.search(r"<[^>]*\son\w+=", html) and "style=" not in html
    assert not re.search(r'(?:src|href)="(?!/|#|https://github\.com/)', html)
    rutas = ("/inicio/inicio.css", "/inicio/inicio.js", "/diseno/patitas.css",
             "/diseno/fuentes.css")
    for ruta in rutas:
        assert c.get(ruta).status_code == 200, ruta


def test_celular_en_una_columna_y_objetivos_de_44_px():
    css = _css()
    celular = css.split("@media (max-width: 860px)", 1)[1]
    assert ".hero { grid-template-columns: minmax(0, 1fr)" in celular
    assert ".nav-enlaces { display: none; }" in celular
    for selector in (".nav-enlaces a", ".boton", ".pie-enlaces a"):
        bloque = re.search(re.escape(selector) + r" \{[^}]*\}", css).group(0)
        assert re.search(r"min-height: (44|52)px", bloque), selector
