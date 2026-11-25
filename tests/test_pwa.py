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
    assert manifiesto["start_url"] == "/app/#reportar"  # #452: instalada, abre en Reportar
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
    """Solo local (#47) y abre sin señal: nada de fuentes o CDN de terceros. La única excepción
    (#430) son las teselas del mapa de OpenStreetMap y el enlace de su atribución."""
    permitidas = {"https://tile.openstreetmap.org/{z}/{x}/{y}.png",
                  "https://www.openstreetmap.org/copyright"}
    for archivo in CARPETA_PWA.iterdir():
        if archivo.suffix in {".html", ".css", ".js", ".webmanifest"}:
            texto = archivo.read_text(encoding="utf-8")
            urls = set(re.findall(r"https?://[^\s'\"]+", texto))
            assert urls <= permitidas, archivo.name
            if urls:
                assert archivo.name == "mapa.js"


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
    # #430: lo único de fuera son las teselas del mapa, solo como imágenes.
    assert re.findall(r"https?://[^\s;]+", politica) == ["https://tile.openstreetmap.org"]


# --- #168: sistema de diseño compartido ------------------------------------------------

def test_la_pwa_usa_el_estilo_de_los_prototipos(c):
    """#428: la PWA usa los colores y las fuentes de los prototipos (/diseno/patitas.css)."""
    html = c.get("/app/").text
    assert re.search(r'<body class="p pwa"', html)
    assert html.index("/diseno/patitas.css") < html.index("estilos.css")
    assert "/diseno/sistema.css" not in html


def test_el_service_worker_guarda_la_hoja_compartida_para_abrir_sin_senal():
    sw = (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
    assert "'/diseno/patitas.css'" in sw
    for archivo in ("'pasos.js'", "'sonido.js'", "'reportar.js'", "'piloto.js'"):
        assert archivo in sw, archivo


def test_la_pwa_valida_que_la_descripcion_tenga_palabras():
    js = (CARPETA_PWA / "reportar.js").read_text(encoding="utf-8")
    assert "Describe con palabras qué le pasa al animal." in js
    assert "MIN_PALABRAS = 4" in js and "VOCALES_MIN = 0.30" in js and "VOCALES_MAX = 0.70" in js


# --- #298: rediseño con el sistema visual nuevo -----------------------------------------

def test_la_pwa_usa_las_fuentes_locales_tambien_sin_senal(c):
    sw = (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
    for recurso in ("/diseno/fuentes/fredoka-latin-wght-normal.woff2",
                    "/diseno/fuentes/nunito-latin-wght-normal.woff2"):
        assert f"'{recurso}'" in sw, recurso
        assert c.get(recurso).status_code == 200
    assert int(re.search(r"patitas-pwa-v(\d+)'", sw).group(1)) >= 12  # #428
    assert "url.pathname.startsWith('/diseno/')" in sw


def test_estilo_propio_de_la_pwa_igual_al_prototipo():
    css = (CARPETA_PWA / "estilos.css").read_text(encoding="utf-8")
    # La pestaña actual se marca con fondo invertido, no solo con color.
    actual = r'\.pestanas a\[aria-current="page"\] \{[^}]*background: var\(--p-tinta\)'
    assert re.search(actual, css)
    # Botones con sombra dura que se hunden al tocarlos; computador desde 900 px.
    assert ".hunde:active:not(:disabled) { translate: 2px 2px;" in css
    assert "@media (min-width: 900px)" in css
    assert "@media (prefers-reduced-motion: reduce)" in css
    assert "data:" not in css  # la CSP no admite imágenes data:


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
    assert "patitas-pwa-v13" in (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")  # #452




# --- #428: reportar en 4 pasos, igual al prototipo ---

def test_reportar_en_cuatro_pasos_con_barra_y_lista(c):
    html = c.get("/app/").text
    pasos = re.findall(r'<div class="paso" data-paso="(\d)"', html)
    assert pasos == ["1", "2", "3", "4"]
    assert re.search(r'data-paso="2"[^>]*hidden', html)  # se ve un paso a la vez
    assert html.count('class="paso-boton" data-ir=') == 4  # lista de pasos en el computador
    assert html.count("<span class=\"progreso-barra\">") == 4  # barra en el celular
    assert 'id="paso-siguiente"' in html and 'aria-label="Paso anterior"' in html
    assert re.search(r'<button type="submit"[^>]*id="enviar"', html)


def test_paso_1_botones_rapidos_y_contador_del_minimo(c):
    html = c.get("/app/").text
    assert html.count('class="sintoma" aria-pressed="false" data-frase=') == 6
    js = (CARPETA_PWA / "reportar.js").read_text(encoding="utf-8")
    assert "'Faltan ' + falta + ' caracteres (mínimo ' + MIN_CARACTERES + ')'" in js
    pasos = (CARPETA_PWA / "pasos.js").read_text(encoding="utf-8")
    assert "innerHTML" not in pasos and "textContent" in pasos


def test_pasos_valida_con_las_mismas_reglas_y_no_cambia_el_envio():
    pasos = (CARPETA_PWA / "pasos.js").read_text(encoding="utf-8")
    for regla in ("reporte.validarDescripcion(", "reporte.validarUbicacion(",
                  "reporte.validarContacto("):
        assert regla in pasos, regla
    assert "fetch(" not in pasos  # el envío sigue solo en reportar.js (cola, piloto, video)


def test_comunas_como_botones_que_cambian_el_valor_que_se_envia(c):
    html = c.get("/app/").text
    assert html.count('class="comuna" data-comuna=') == 11
    assert re.search(r'<select id="comuna" name="comuna" hidden>', html)


def test_gracias_con_codigo_grande_copiar_y_sello(c):
    gracias = _seccion(c.get("/app/").text, "pantalla-codigo")
    assert 'class="sello-huella"' in gracias and 'id="copiar"' in gracias
    assert 'class="big mono" id="codigo-grande"' in gracias
    app = (CARPETA_PWA / "app.js").read_text(encoding="utf-8")
    assert "navigator.clipboard.writeText(codigo)" in app


def test_sonidos_suaves_con_interruptor_y_sin_musica(c):
    html = c.get("/app/").text
    boton = r'<button[^>]*id="sonido"[^>]*aria-label="Sonidos al tocar" aria-pressed='
    assert re.search(boton, html)
    sonido = (CARPETA_PWA / "sonido.js").read_text(encoding="utf-8")
    assert "setInterval" not in sonido and "musica" not in sonido.lower()  # nada en bucle
    assert "localStorage" in sonido and "try {" in sonido


def test_los_sonidos_de_la_pwa_y_del_panel_son_los_mismos():
    """Las recetas comunes (pop, siguiente, atrás) no se separan entre la PWA y el panel."""
    sonido = (CARPETA_PWA / "sonido.js").read_text(encoding="utf-8")
    panel = (CARPETA_PWA.parents[1] / "panel" / "src" / "sonido.ts").read_text(encoding="utf-8")
    for nombre, frecuencias in (("pop", "560"), ("siguiente", "523, 784"), ("atras", "659, 440")):
        assert re.search(rf'case "{nombre}": return [^;]*{frecuencias}', panel), nombre
        pwa = re.search(rf"{nombre}: \[(.*?)\],\n", sonido, re.S).group(1)
        assert all(f in pwa for f in frecuencias.split(", ")), nombre


def test_un_solo_inicio_la_app_abre_en_reportar_y_la_consulta_sin_prioridad(c):
    # #452: la portada vieja de /app/ ya no existe; «Inicio» y el logo llevan a la principal.
    html = c.get("/app/").text
    assert 'id="pantalla-inicio"' not in html and "no debería esperar" not in html
    assert '<a class="marca" href="/">' in html and '<a href="/" class="solo-pc">Inicio</a>' in html
    assert 'href="#inicio"' not in html
    app = (CARPETA_PWA / "app.js").read_text(encoding="utf-8")
    assert "mostrarPantalla('inicio')" not in app and "fotosDeLaPortada" not in app
    assert '<img src="/inicio/img/animales/max.jpg"' in html  # foto fija, sin el catálogo
    estado = _seccion(html, "pantalla-estado").lower()
    assert "prioridad" not in estado  # RN-14: el ciudadano nunca ve la prioridad


# --- #430: mapa con Leaflet y OpenStreetMap ---

def test_el_mapa_solo_abre_las_teselas_de_osm_como_imagen(c):
    politica = c.get("/app/").headers["content-security-policy"]
    directivas = dict(d.strip().split(" ", 1) for d in politica.split(";"))
    assert "https://tile.openstreetmap.org" in directivas["img-src"]
    for otra in ("script-src", "style-src", "connect-src", "default-src"):
        assert "openstreetmap" not in directivas[otra], otra


def test_las_teselas_envian_el_origen_y_la_pagina_sigue_sin_referer(c):
    # OSM bloquea (403, «Access blocked») las teselas que llegan sin Referer (arreglos, parte D).
    assert c.get("/app/").headers["referrer-policy"] == "no-referrer"
    politica = "referrerPolicy: 'strict-origin-when-cross-origin'"
    assert politica in (CARPETA_PWA / "mapa.js").read_text(encoding="utf-8")
    panel = CARPETA_PWA.parents[1] / "panel" / "src" / "MiniMapa.tsx"
    assert 'referrerPolicy: "strict-origin-when-cross-origin"' in panel.read_text(encoding="utf-8")


def test_leaflet_va_dentro_del_repositorio_con_su_licencia(c):
    carpeta = CARPETA_PWA / "vendor" / "leaflet"
    assert "BSD" in (carpeta / "LICENSE").read_text(encoding="utf-8")
    html = c.get("/app/").text
    assert 'src="vendor/leaflet/leaflet.js"' in html and 'href="vendor/leaflet/leaflet.css"' in html
    assert c.get("/app/vendor/leaflet/leaflet.js").status_code == 200
    mapa = (CARPETA_PWA / "mapa.js").read_text(encoding="utf-8")
    assert "© <a href=\"https://www.openstreetmap.org/copyright\">OpenStreetMap</a>" in mapa


def test_el_mapa_usa_los_mismos_campos_y_nunca_bloquea_el_envio():
    mapa = (CARPETA_PWA / "mapa.js").read_text(encoding="utf-8")
    assert "window.PatitasReporte.ponerUbicacion(" in mapa  # latitud y longitud de siempre
    assert "fetch(" not in mapa and "submit" not in mapa and "innerHTML" not in mapa
    assert "sinMapa(" in mapa and "navigator.onLine === false" in mapa  # sin red, sin mapa
    sw = (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
    assert "openstreetmap" not in sw  # las teselas no se guardan en el teléfono


def test_consultar_es_publico_y_no_muestra_mapa_ni_direccion(c):
    estado = _seccion(c.get("/app/").text, "pantalla-estado")
    assert "mapa" not in estado.lower() and "direccion" not in estado.lower()
    js = (CARPETA_PWA / "app.js").read_text(encoding="utf-8")
    assert "leaflet" not in js.lower() and "L.map" not in js


def test_reportar_en_computador_tiene_panel_de_ayuda_que_el_telefono_oculta(c):
    # Arreglos, parte D: pasos · formulario · foto real con «Un veterinario revisa tu reporte» y
    # «Mientras llega la ayuda» (3 consejos). En el teléfono el panel derecho no se ve.
    html = c.get("/app/").text
    panel = html[html.index('<aside class="reportar-ayuda solo-pc"'):]
    panel = panel[:panel.index("</aside>")]
    assert "animales/max.jpg" in panel and "Un veterinario revisa tu reporte" in panel
    assert "Mientras llega la ayuda" in panel and panel.count("<li>") == 3
    css = (CARPETA_PWA / "estilos.css").read_text(encoding="utf-8")
    assert ".reportar-ayuda { display: none; }" in css
    tres = css[css.index("@media (min-width: 1024px)"):]
    assert '"titulo cuerpo ayuda"' in tres and "max-width: 1280px" in tres
    assert "grid-template-rows: auto 1fr" in css  # sin el hueco entre el título y los pasos
