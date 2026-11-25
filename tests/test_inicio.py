"""Página de inicio pública en la raíz del sitio (#145; rediseño igual al prototipo, #426)."""
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


def test_secciones_del_prototipo_en_orden_y_sin_tecnologia():
    html = _html()
    marcas = ['class="hero', 'class="cuadros', 'class="recorrido"', 'class="cifras',
              'id="problema"', 'id="como"', 'class="adopcion"', 'id="roles"', 'class="ayuda"',
              'class="final', 'class="pie"']
    posiciones = [html.index(m) for m in marcas]
    assert posiciones == sorted(posiciones)
    assert "Tecnología" not in html and "FastAPI" not in html
    assert re.search(r'<h1 id="titulo" class="h may">Un animal herido <span class="resalto">'
                     r'<span>no debería</span></span> esperar</h1>', html)


def test_los_enlaces_llevan_a_las_partes_reales(c):
    html = c.get("/").text
    assert html.count('href="/app/#reportar"') >= 4  # nav, hero, cuadro, ayuda y CTA final
    assert 'href="/app/#estado"' in html and 'href="/panel/#registro"' in html
    assert 'href="/panel/"' in html and 'href="/docs"' in html
    assert 'href="https://github.com/Brizad/patitas-en-casa"' in html


def test_seis_pasos_siete_roles_y_tres_formas_de_ayudar():
    html = _html()
    assert len(re.findall(r'<li class="paso paso-\d', html)) == 6
    for rol in ("ciudadano", "veterinario", "rescatista", "coordinador", "adoptante",
                "administrador", "alcaldia"):
        assert f'class="rol rol-{rol} tarjeta"' in html, rol
    assert "¿Eres del equipo?" in html
    for ayuda in ("Reporta", "Adopta", "Comparte"):
        assert f'<h3 class="h may">{ayuda}</h3>' in html
    assert '<button class="ayuda-accion" type="button" id="compartir"' in html
    assert 'id="compartido" role="status"' in html


def test_las_cifras_nunca_se_inventan():
    html, js = _html(), _js()
    valores = re.findall(r'data-cifra="(\w+)">([^<]*)<', html)
    assert [k for k, _ in valores] == ["reportes", "rescatados", "adoptados"]
    assert all(v == "—" for _, v in valores)  # sin dato, «—»
    assert '"/indicadores/publicos"' in js and "Number.isInteger(valor)" in js


def test_fotos_y_animales_reales_del_catalogo():
    html, js = _html(), _js()
    for nombre in ("Pinina", "Mochi", "Lupe", "Winny", "Pecas", "Max"):
        assert f'data-animal="{nombre}"' in html, nombre
    assert '"/adopciones/animales"' in js and 'id="en-adopcion"' in html
    assert "innerHTML" not in js  # los datos se ponen con textContent (XSS)
    assert 'img.addEventListener("error", () => img.remove())' in js  # nunca una foto rota


def test_usa_la_misma_csp_estricta_y_sus_archivos_se_sirven(c):
    raiz = c.get("/")
    assert "script-src 'self'" in raiz.headers["content-security-policy"]
    for ruta, tipo in (("/inicio/inicio.css", "text/css"), ("/inicio/inicio.js", "javascript"),
                       ("/diseno/patitas.css", "text/css")):
        r = c.get(ruta)
        assert r.status_code == 200 and tipo in r.headers["content-type"], ruta


def test_sin_scripts_en_linea_ni_estilos_en_linea_ni_recursos_externos():
    html = _html()
    assert re.findall(r"<script[^>]*>", html) == ['<script src="/inicio/inicio.js" defer>']
    assert not re.search(r"<[^>]*\son\w+=", html) and "style=" not in html
    assert not re.search(r'(?:src|href)="(?!/|#|https://github\.com/)', html)
    css = _css()
    assert "@import" not in css and not re.search(r"url\((?!/|#)", css)


def test_fuentes_locales_de_los_prototipos(c):
    css = (RAIZ / "app" / "diseno" / "patitas.css").read_text(encoding="utf-8")
    for fuente in ("fredoka-latin-wght-normal.woff2", "nunito-latin-wght-normal.woff2"):
        assert f"url(/diseno/fuentes/{fuente})" in css
        assert c.get(f"/diseno/fuentes/{fuente}").status_code == 200
    assert "fonts.googleapis" not in css


def test_celular_en_una_columna_y_objetivos_de_44_px():
    css = _css()
    celular = css.split("@media (max-width: 760px)", 1)[1]
    assert ".hero, .dos-columnas { grid-template-columns: minmax(0, 1fr)" in celular
    assert ".nav-enlaces { display: none; }" in celular
    for selector in (".nav-enlaces a", ".pausa-etiqueta", ".ayuda-accion", ".pie-enlaces a"):
        bloque = re.search(re.escape(selector) + r" \{[^}]*\}", css).group(0)
        assert "min-height: 44px" in bloque, selector


# --- El recorrido de huellas de #328 se reutiliza; el movimiento se pausa o se reduce. ---

def test_huellas_de_perro_y_gato_decorativas_sobre_la_curva():
    html = _html()
    svg = re.search(r'<svg class="rastro"[^>]*>', html).group(0)
    assert 'aria-hidden="true"' in svg and 'focusable="false"' in svg
    assert html.count('href="#huella-perro"') >= 10 and html.count('href="#huella-gato"') >= 10


def test_la_caminata_es_escalonada_y_sin_parpadeo():
    css = _css()
    assert re.search(r"\.rastro use \{[^}]*animation: pisar 8s", css)
    retrasos = [float(r) for r in re.findall(r"\.t\d+ \{ animation-delay: ([\d.]+)s; \}", css)]
    assert len(retrasos) == 15 and retrasos == sorted(retrasos)
    pulso = float(re.search(r"animation: pulsar ([\d.]+)s", css).group(1))
    assert pulso >= 0.34  # nada destella más de 3 veces por segundo (WCAG 2.3.1)


def test_se_puede_pausar_lo_que_se_mueve_sin_javascript():
    html, css = _html(), _css()
    assert '<input class="pausa" type="checkbox" id="pausar">' in html
    assert '<label class="pausa-etiqueta" for="pausar">Pausar animaciones</label>' in html
    assert "body:has(.pausa:checked) * { animation-play-state: paused !important; }" in css


def test_con_movimiento_reducido_todo_queda_quieto():
    reducido = _css().split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "animation: none !important; transition: none !important;" in reducido
    assert ".pausa, .pausa-etiqueta { display: none; }" in reducido
