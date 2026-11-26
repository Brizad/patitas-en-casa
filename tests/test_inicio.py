"""Página de inicio pública en la raíz del sitio (#145; inicio v3: paleta del adoptante, hero lila
estilo Petgon y bloques con borde y sombra dura)."""
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


def test_paleta_del_adoptante_sin_naranja_y_fredoka_en_los_titulos():
    css, html = _css(), _html()
    for color in ("#FFF8EE", "#7A5AF8", "#9B83FA", "#E8508A", "#FBD9E3", "#FFD23F", "#D7F0DC",
                  "#2B2340"):
        assert color in css, color
    assert "#F2603A" not in css and "naranja" not in css  # inicio v3: sin naranja
    assert "/diseno/fuentes.css" not in html and "serif" not in html  # sin la serifa del hero
    # Botones como el adoptante: borde oscuro de 2,5 px y sombra dura.
    assert re.search(r"\.btn \{[^}]*border: 2\.5px solid var\(--oscuro\)", css)
    assert re.search(r"\.nav \{[^}]*background: var\(--amarillo\); border-bottom: 3px solid", css)


def test_hero_lila_con_burbujas_en_las_o_y_capsula_con_la_ilustracion():
    html, css = _html(), _css()
    assert '<span class="oculto">Adopta amor, reporta a tiempo</span>' in html
    titulo = html[html.index('<h1 id="titulo"'):html.index("</h1>")]
    assert titulo.count('class="burbuja burbuja--') == 3 and "animales/lupe.jpg" in titulo
    assert '<span class="hero-amarillo">a tiempo</span>' in titulo
    assert html.count('class="flor ') == 2 and 'class="capsula"' in html
    assert 'src="/inicio/img/ilustracion-gatos.jpg"' in html
    assert re.search(r"\.hero \{[^}]*background: var\(--lila\)", css)


def test_secciones_en_orden_como_el_prototipo():
    html = _html()
    marcas = ['class="hero"', 'class="cinta"', 'class="bloque-oscuro"', 'class="bloque-rosa"',
              'class="cuadros"', 'class="adopcion"', 'class="ayuda-lila"', 'id="equipo"',
              'class="ayuda-foto"', 'class="ayuda-noche"', 'id="roles"', 'class="final-caja"',
              'class="carril"', 'class="pie"', 'class="pie-perro"', 'pie-final"']
    posiciones = [html.index(m) for m in marcas]
    assert posiciones == sorted(posiciones)
    assert html.count('<li class="rol rol-') == 8 and "¿Eres del equipo?" in html
    assert "Diseñado y desarrollado por" in html and "Brayan David Amado Ramírez" in html
    assert "© 2026 Patitas en Casa · Cúcuta, Colombia" in html and "por Brayan Amado" in html
    assert ">Plataforma</p>" in html and "Para refugios y su equipo" in html  # cambio 2: producto


def test_ilustraciones_del_repo_optimizadas_y_con_texto_alternativo(c):
    html = _html()
    for nombre in ("gatos", "gato-lago", "gato-arbol", "perro"):
        archivo = CARPETA / "img" / f"ilustracion-{nombre}.jpg"
        assert archivo.stat().st_size < 160_000, nombre  # optimizadas
        img = re.search(rf'<img src="/inicio/img/ilustracion-{nombre}\.jpg"[^>]*>', html).group(0)
        assert re.search(r'alt="Ilustración de [^"]{20,}"', img), nombre
        r = c.get(f"/inicio/img/ilustracion-{nombre}.jpg")
        assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg", nombre


def test_sin_rastro_de_huellas_ni_pausa_ni_nota_de_cifras():
    html, css = _html(), _css()
    assert 'class="rastro"' not in html and "huella-perro" not in html
    assert "Pausar animaciones" not in html and "pausa" not in css
    assert "Cifras en vivo" not in html and "aún sin dato" not in html
    assert "@media (prefers-reduced-motion: reduce)" in css  # el movimiento se apaga por CSS


def test_las_cifras_nunca_se_inventan():
    html, js = _html(), _js()
    valores = re.findall(r'data-cifra="(\w+)">([^<]*)<', html)
    assert {k for k, _ in valores} == {"reportes", "en_adopcion"}
    assert all(v == "—" for _, v in valores)  # sin dato, «—»
    assert '"/indicadores/publicos"' in js and "Number.isInteger(valor)" in js
    assert 'ponerCifra("en_adopcion", lista.length)' in js


def test_fotos_fijas_del_diseno_son_estaticas_y_siempre_cargan(c):
    # #452: el hero y las secciones no dependen del catálogo (Render puede estar despertando).
    html = _html()
    assert "data-animal" not in html
    for nombre in ("lupe", "cascabel", "copo", "nube", "toby"):
        assert f'<img src="/inicio/img/animales/{nombre}.jpg"' in html, nombre
        archivo = CARPETA / "img" / "animales" / f"{nombre}.jpg"
        assert archivo.stat().st_size < 60_000, nombre
        assert c.get(f"/inicio/img/animales/{nombre}.jpg").status_code == 200, nombre
    titulo = html[html.index('<h1 id="titulo"'):html.index("</h1>")]
    assert '<img src="/inicio/img/animales/lupe.jpg"' in titulo


def test_fotos_del_catalogo_se_reintentan_y_la_huella_solo_si_no_hay_foto():
    js = _js()
    assert '"/adopciones/animales"' in js and "innerHTML" not in js
    assert "for (let intento = 0; intento < 6; intento++)" in js  # mientras Render despierta
    assert "new AbortController()" in js
    assert "if (intentos < 3)" in js and "img.replaceWith(huella())" in js  # nunca rota
    assert 'foto.append(animal.foto ? imagen(animal, "") : huella());' in js


def test_los_enlaces_llevan_a_las_partes_reales(c):
    html = c.get("/").text
    assert html.count('href="/app/#reportar"') >= 4
    assert 'href="/app/#estado"' in html and 'href="/panel/#adoptar"' in html
    assert 'href="/panel/#personal"' in html and 'href="/docs"' in html
    assert '<button class="btn btn--blanco" type="button" id="compartir"' in html


def test_misma_csp_estricta_sin_scripts_ni_estilos_en_linea(c):
    raiz = c.get("/")
    assert "script-src 'self'" in raiz.headers["content-security-policy"]
    html = _html()
    assert re.findall(r"<script[^>]*>", html) == ['<script src="/inicio/inicio.js" defer>']
    assert not re.search(r"<[^>]*\son\w+=", html) and "style=" not in html
    assert not re.search(r'(?:src|href)="(?!/|#)', html)  # nada externo (tarea 6: ni GitHub)
    rutas = ("/inicio/inicio.css", "/inicio/inicio.js", "/diseno/patitas.css",
             "/diseno/fuentes.css")
    for ruta in rutas:
        assert c.get(ruta).status_code == 200, ruta


def test_celular_en_una_columna_y_objetivos_de_44_px():
    css = _css()
    celular = css.split("@media (max-width: 760px)", 1)[1]
    una_columna = (".bloques-fila, .cuadros, .ayuda, .ayuda-fila, .final-caja, .pie-fila,"
                   " .tarjetas, .roles { grid-template-columns: minmax(0, 1fr); }")
    assert una_columna in celular
    assert ".nav-enlaces { display: none; }" in celular
    assert ".hero-titulo { font-size: clamp(30px, 11vw, 44px)" in celular
    assert ".burbuja { width: clamp(38px, 12.5vw, 50px)" in celular
    assert ".pie-perro { display: none; }" in css  # la tarjeta del perro, solo en computador
    for selector in (".nav-enlaces a", ".btn", ".pie-enlaces a"):
        bloque = re.search(re.escape(selector) + r" \{[^}]*\}", css).group(0)
        assert re.search(r"min-height: (44|46)px", bloque), selector


def test_menu_fijo_compacto_al_bajar_y_boton_de_menu_en_el_celular():
    html, css, js = _html(), _css(), _js()
    assert re.search(r"\.nav \{ position: sticky; top: 0; z-index: 100;", css)
    assert ".nav.compacta .nav-fila { min-height: 64px; }" in css and "min-height: 76px" in css
    assert "scroll-margin-top: 84px" in css and "scroll-behavior: smooth" in css
    suave = "@media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }"
    assert suave in css
    boton = re.search(r'<button class="nav-menu"[^>]*>', html).group(0)
    assert 'aria-label="Abrir el menú"' in boton and 'aria-expanded="false"' in boton
    assert 'aria-controls="menu-principal"' in boton
    assert '<nav class="nav-enlaces" id="menu-principal"' in html
    assert 'barra.classList.toggle("compacta", window.scrollY > 20)' in js
    assert 'if (e.target.closest("a")) abrir(false)' in js  # se cierra al tocar un enlace
