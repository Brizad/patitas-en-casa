"""HU-08, parte 2: la PWA ciudadana servida por la API (#59, decisión de #47).

La lógica de la pantalla está en app/pwa/app.js; aquí se prueba lo que la API entrega y las
reglas que el JavaScript debe respetar (sin recursos externos, sin innerHTML con datos).
"""
import json
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

CARPETA_PWA = Path(__file__).resolve().parents[1] / "app" / "pwa"


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


def test_la_pwa_sirve_la_pantalla_de_consulta(c):
    respuesta = c.get("/app/")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/html")
    html = respuesta.text
    assert '<html lang="es">' in html
    assert "Estado del reporte" in html
    assert 'rel="manifest" href="manifest.webmanifest"' in html
    assert 'name="viewport"' in html


@pytest.mark.parametrize("archivo, tipo", [
    ("estilos.css", "text/css"), ("app.js", "javascript"), ("sw.js", "javascript"),
    ("icono.svg", "image/svg+xml"), ("manifest.webmanifest", "manifest+json"),
])
def test_los_archivos_de_la_pwa_se_sirven_con_su_tipo(c, archivo, tipo):
    respuesta = c.get(f"/app/{archivo}")
    assert respuesta.status_code == 200
    assert tipo in respuesta.headers["content-type"]


def test_el_manifiesto_describe_una_pwa_instalable(c):
    manifiesto = json.loads(c.get("/app/manifest.webmanifest").text)
    assert manifiesto["lang"] == "es"
    assert manifiesto["start_url"] == "/app/"
    assert manifiesto["scope"] == "/app/"
    assert manifiesto["display"] == "standalone"
    assert manifiesto["icons"] and all(i["src"] for i in manifiesto["icons"])


def test_la_pwa_tiene_una_politica_de_contenido_estricta(c):
    cabeceras = c.get("/app/").headers
    politica = cabeceras["content-security-policy"]
    assert "default-src 'self'" in politica
    assert "script-src 'self'" in politica
    assert "unsafe-inline" not in politica.split("script-src")[1].split(";")[0]
    assert cabeceras["x-content-type-options"] == "nosniff"


def test_la_api_no_lleva_la_politica_de_la_pwa(c):
    """La CSP es de la PWA; /docs (Swagger) necesita sus propios scripts."""
    assert "content-security-policy" not in c.get("/docs").headers


def test_la_pwa_no_carga_recursos_externos():
    """Solo local (#47) y abre sin señal: nada de fuentes o CDN de terceros."""
    for archivo in CARPETA_PWA.iterdir():
        if archivo.suffix in {".html", ".css", ".js", ".webmanifest"}:
            texto = archivo.read_text(encoding="utf-8")
            assert not re.search(r"https?://", texto), archivo.name


def test_el_javascript_no_inserta_datos_como_html():
    """Los pasos llegan de la API: se pintan con textContent, nunca con innerHTML (XSS)."""
    js = (CARPETA_PWA / "app.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js
    assert "/reportes/" in js and "/seguimiento" in js


def test_el_service_worker_no_guarda_respuestas_de_la_api():
    """Privacidad y datos frescos: solo se guarda la interfaz de /app/."""
    sw = (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
    assert "/reportes/" in sw  # la regla que excluye la API está escrita
    assert "cache.put" not in sw


# --- #61: pantalla Reportar emergencia y envío sin conexión (RF-12) --------------------

def test_la_pwa_sirve_el_formulario_de_reporte(c):
    html = c.get("/app/").text
    assert "Reportar emergencia" in html
    assert 'id="reporte"' in html
    assert 'id="descripcion"' in html and 'minlength="20"' in html  # RN-01
    assert 'id="direccion"' in html and 'id="usar-gps"' in html
    assert 'id="comuna"' in html
    assert "TU CÓDIGO DE SEGUIMIENTO" in html
    assert 'src="reportar.js"' in html


def test_la_comuna_ofrece_solo_las_10_de_cucuta(c):
    html = c.get("/app/").text
    lista = html.split('id="comuna"')[1].split("</select>")[0]
    opciones = re.findall(r'<option value="(\d*)"', lista)
    assert opciones == [""] + [str(n) for n in range(1, 11)]


def test_el_html_no_usa_estilos_ni_scripts_en_linea(c):
    """La CSP bloquea style="" y <script> sin src: si se usaran, la pantalla se rompería."""
    html = c.get("/app/").text
    assert "style=" not in html
    assert not re.search(r"<script(?![^>]*\ssrc=)", html)
    assert not re.search(r"\son[a-z]+=", html)  # onclick="…"


def test_reportar_js_envia_con_clave_de_idempotencia():
    js = (CARPETA_PWA / "reportar.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js
    assert "'/reportes'" in js and "Idempotency-Key" in js
    assert "crypto.getRandomValues" in js  # la clave la genera el navegador


def test_reportar_js_guarda_sin_senal_y_reintenta_al_volver():
    js = (CARPETA_PWA / "reportar.js").read_text(encoding="utf-8")
    assert "localStorage" in js
    assert "'online'" in js  # evento al volver la conexión


def test_el_service_worker_guarda_la_nueva_pantalla():
    sw = (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
    assert "'reportar.js'" in sw
    assert "patitas-pwa-v1'" not in sw  # versión nueva: los teléfonos bajan la interfaz nueva


def test_video_opcional_en_el_formulario_y_blob_solo_local():
    """#125: el video se elige en el formulario; la CSP admite blob: (archivos del propio
    navegador) para leer su duración y mostrar la tira, pero ningún servidor externo."""
    c = TestClient(crear_app(RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("D", 40)),
                             repositorio_usuarios=RepositorioUsuariosEnMemoria(),
                             emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-car")))
    respuesta = c.get("/app/")
    assert 'id="video"' in respuesta.text and 'accept="video/mp4' in respuesta.text
    politica = respuesta.headers["Content-Security-Policy"]
    assert "img-src 'self' blob:" in politica and "media-src blob:" in politica
    assert "http" not in politica


# --- #168: sistema de diseño compartido ------------------------------------------------

def test_la_pwa_usa_el_sistema_de_diseno(c):
    html = c.get("/app/").text
    assert re.search(r"<body[^>]*class=\"ds\"", html)
    assert html.index("/diseno/sistema.css") < html.index("estilos.css")
    assert 'class="ds-btn ds-btn--pri' in html and 'class="ds-tarjeta"' in html


def test_el_service_worker_guarda_la_hoja_compartida_para_abrir_sin_senal():
    sw = (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
    assert "/diseno/sistema.css" in sw
    assert "patitas-pwa-v3'" not in sw  # versión nueva: se baja la interfaz rediseñada


def test_la_pwa_valida_que_la_descripcion_tenga_palabras():
    js = (CARPETA_PWA / "reportar.js").read_text(encoding="utf-8")
    assert "Describe con palabras qué le pasa al animal." in js
    assert "MIN_PALABRAS = 4" in js and "VOCALES_MIN = 0.30" in js and "VOCALES_MAX = 0.70" in js


# --- #298: rediseño con el sistema visual nuevo -----------------------------------------

def test_la_pwa_usa_las_fuentes_locales_tambien_sin_senal(c):
    html = c.get("/app/").text
    assert html.index("/diseno/fuentes.css") < html.index("/diseno/sistema.css")
    sw = (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
    for recurso in ("/diseno/fuentes.css", "/diseno/fuentes/eb-garamond-latin-400-normal.woff2",
                    "/diseno/fuentes/figtree-latin-wght-normal.woff2"):
        assert f"'{recurso}'" in sw, recurso
    # #298 la subió a v9 (interfaz rediseñada); #308 a v10 (ícono nuevo).
    assert int(re.search(r"patitas-pwa-v(\d+)'", sw).group(1)) >= 9
    assert "url.pathname.startsWith('/diseno/')" in sw


def test_estilo_propio_de_la_pwa_con_el_sistema_nuevo():
    css = (CARPETA_PWA / "estilos.css").read_text(encoding="utf-8")
    # Pestañas como control segmentado: la actual se marca con fondo invertido, no solo color.
    actual = r'\.pestanas a\[aria-current="page"\] \{[^}]*background: var\(--ds-tinta\)'
    assert re.search(actual, css)
    assert "border-radius: var(--pc-radio-pildora)" in css  # cabecera y pestañas en píldora
    assert re.search(r"\.big \{[^}]*background: var\(--ds-accion\)", css)  # código en lavanda
    assert "dashed" not in css and "box-shadow" not in css


def test_los_enlaces_con_forma_de_boton_no_toman_el_color_de_enlace():
    """#298: «Reportar otra emergencia» es un <a class="ds-btn">; la regla general de enlaces
    no debe ganarle al botón (antes salía en verde)."""
    css = (CARPETA_PWA.parent / "diseno" / "sistema.css").read_text(encoding="utf-8")
    assert ":where(.ds) a {" in css and not re.search(r"^\.ds a \{", css, re.M)


# --- H-1, H-2 y arranque en frío de Render ---

def _seccion(html: str, id_: str) -> str:
    inicio = html.index(f'id="{id_}"')
    return html[inicio:html.index("</section>", inicio)]


def test_h1_gracias_por_avisar_dice_que_hacer_mientras_llega_ayuda(c):
    gracias = _seccion(c.get("/app/").text, "pantalla-codigo")
    assert "Mientras llega ayuda" in gracias and gracias.count("<li>") == 3
    assert "iguales para todos los reportes" in gracias


def test_h1_los_consejos_no_dependen_de_la_prioridad_rn14(c):
    """RN-14: el ciudadano nunca ve la prioridad. Los consejos son texto fijo del HTML y
    ningún script de la PWA lee la prioridad para elegirlos."""
    gracias = _seccion(c.get("/app/").text, "pantalla-codigo").lower()
    for palabra in ("prioridad", "crítica", "critica", "urgente", "grave"):
        assert palabra not in gracias
    for archivo in ("app.js", "reportar.js", "video.js"):
        js = (CARPETA_PWA / archivo).read_text(encoding="utf-8")
        assert "prioridad" not in js and "mientras-llega" not in js


def test_h2_el_aviso_sin_conexion_arranca_oculto_y_depende_de_navigator_online(c):
    html = c.get("/app/").text
    assert 'id="aviso-sin-conexion" role="status" hidden' in html
    js = (CARPETA_PWA / "app.js").read_text(encoding="utf-8")
    assert "$('aviso-sin-conexion').hidden = navigator.onLine !== false" in js
    assert "'offline', pintarConexion" in js and "'online', pintarConexion" in js


def test_si_el_servidor_tarda_la_pwa_dice_que_esta_despertando():
    app = (CARPETA_PWA / "app.js").read_text(encoding="utf-8")
    reportar = (CARPETA_PWA / "reportar.js").read_text(encoding="utf-8")
    assert "El servidor está despertando" in app and "avisarSiTarda" in app
    assert "window.Patitas.avisarSiTarda" in reportar and "Tu reporte no se pierde" in reportar


def test_el_service_worker_cambia_de_version_para_que_llegue_la_pantalla_nueva():
    assert "patitas-pwa-v11" in (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
