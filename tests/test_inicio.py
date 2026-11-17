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
    compartida = (CARPETA.parent / "diseno" / "sistema.css").read_text(encoding="utf-8")
    assert "'EB Garamond'" in compartida and "'Figtree'" in compartida  # #296: tokens compartidos
    assert "var(--pc-serif)" in _css()
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


def _temas():
    """Variables en claro y en oscuro: primero la hoja compartida y encima la de la portada."""
    claro, oscuro = {}, {}
    for css in ((CARPETA.parent / "diseno" / "sistema.css").read_text(encoding="utf-8"), _css()):
        luz, noche = css.split("@media (prefers-color-scheme: dark)", 1)
        claro.update(re.findall(r"--([\w-]+):\s*([^;]+);", luz.split("/* Base", 1)[0]))
        noche = noche.split("/* Base", 1)[0].split("}", 2)[0]
        oscuro.update(re.findall(r"--([\w-]+):\s*([^;]+);", noche))
    return claro, {**claro, **oscuro}


def _color(tema, nombre):
    valor = tema[nombre].strip()
    while (m := re.fullmatch(r"var\(--([\w-]+)\)", valor)):
        valor = tema[m.group(1)].strip()
    return valor


def test_colores_con_contraste_aa_en_claro_y_oscuro():
    claro, oscuro = _temas()
    assert _color(claro, "suave").lower() != "#8a8a80"  # el gris de DESIGN.md no llega a 4,5:1
    for tema in (claro, oscuro):
        for texto, fondo in (("texto", "lienzo"), ("suave", "lienzo"), ("sobre-camara", "camara"),
                             ("tinta", "lavanda"), ("crema", "bosque"), ("crema", "rol")):
            assert _contraste(_color(tema, texto), _color(tema, fondo)) >= 4.5, (texto, fondo)


# --- Portada con carácter (#328): titular bicolor, huellas que caminan y movimiento reducido. ---

def _html():
    return (CARPETA / "index.html").read_text(encoding="utf-8")


def _reducido():
    return _css().split("@media (prefers-reduced-motion: reduce)", 1)[1]


def test_titular_en_dos_tonos_de_44_a_120_px():
    assert re.search(r'<h1 id="titulo"><span class="linea tenue">Un animal herido,</span> '
                     r'<span class="linea">no debería esperar\.</span></h1>', _html())
    assert re.search(r"\.tenue \{ color: var\(--suave\); \}", _css())  # el gris accesible
    m = re.search(r"\.portada h1 \{[^}]*clamp\(([\d.]+)rem, ([\d.]+)rem \+ ([\d.]+)vw, "
                  r"([\d.]+)rem\)", _css())
    minimo, base, vw, maximo = map(float, m.groups())
    assert minimo * 16 == 44 and maximo * 16 == 120
    assert abs(base * 16 + vw * 14.4 - 120) < 0.5  # llega a 120 px justo a 1440 px


def test_la_portada_tiene_una_sola_accion_principal():
    portada = re.search(r'<section class="portada".*?</section>', _html(), re.S).group(0)
    assert portada.count('class="boton urgente"') == 1 and portada.count('class="boton') == 1


def test_huellas_de_perro_y_gato_decorativas_sobre_la_curva():
    html = _html()
    svg = re.search(r'<svg class="rastro"[^>]*>', html).group(0)
    assert 'aria-hidden="true"' in svg and 'focusable="false"' in svg
    assert html.count('href="#huella-perro"') >= 10 and html.count('href="#huella-gato"') >= 10
    assert 'class="perro t0' in html and " banda" in html  # empieza a la izquierda; pisa la banda
    assert '<g class="onda"' in html  # la píldora con barritas en el centro de la curva


def test_la_caminata_es_escalonada_y_sin_parpadeo():
    css = _css()
    assert re.search(r"\.rastro use \{[^}]*animation: pisar 8s", css)
    retrasos = [float(r) for r in re.findall(r"\.t\d+ \{ animation-delay: ([\d.]+)s; \}", css)]
    assert len(retrasos) == 15 and retrasos == sorted(retrasos)  # .t1 … .t15, en orden
    pulso = float(re.search(r"animation: pulsar ([\d.]+)s", css).group(1))
    assert pulso >= 0.34  # nada destella más de 3 veces por segundo (WCAG 2.3.1)


def test_con_movimiento_reducido_todo_queda_quieto():
    reducido = _reducido()
    for selector in (".linea", ".rastro use", ".onda rect"):
        assert selector in reducido.split("animation: none", 1)[0], selector
    assert ".boton, .pildora { transition: none; }" in reducido


def test_se_puede_pausar_lo_que_se_mueve_sin_javascript():
    html, css = _html(), _css()
    assert '<input class="pausa" type="checkbox" id="pausar">' in html
    assert '<label class="pausa-etiqueta" for="pausar">Pausar animaciones</label>' in html
    assert "body:has(.pausa:checked) * { animation-play-state: paused !important; }" in css


def test_el_css_no_carga_nada_de_fuera():
    css = _css()
    assert "@import" not in css and not re.search(r"url\((?!/|#)", css)
    assert not re.search(r'(?:src|href)="(?!/|#|https://github\.com/)', _html())
