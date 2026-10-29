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


def test_la_raiz_lleva_a_la_pwa(c):
    respuesta = c.get("/", follow_redirects=False)
    assert respuesta.status_code in (302, 307)
    assert respuesta.headers["location"] == "/app/"


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
