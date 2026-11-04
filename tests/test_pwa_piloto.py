"""Modo piloto en la PWA (RNF-06, #258). El recorrido completo en el navegador está en
e2e/piloto.spec.mjs; aquí se protege lo que evita mezclar la prueba con reportes reales."""
import re
from pathlib import Path

PWA = Path(__file__).resolve().parents[1] / "app" / "pwa"
HTML = (PWA / "index.html").read_text(encoding="utf-8")
PILOTO = (PWA / "piloto.js").read_text(encoding="utf-8")
REPORTAR = (PWA / "reportar.js").read_text(encoding="utf-8")


def test_el_modo_piloto_se_carga_antes_que_la_app_y_empieza_oculto():
    assert HTML.index('src="piloto.js"') < HTML.index('src="app.js"')
    assert re.search(r'id="aviso-piloto"[^>]*hidden', HTML)
    assert re.search(r'id="pantalla-sus"[^>]*hidden', HTML)
    assert re.search(r'id="ir-sus"[^>]*hidden', HTML)


def test_un_reporte_de_prueba_nunca_entra_a_la_cola_sin_senal():
    assert "!piloto && escribirCola(" in REPORTAR
    inicio = REPORTAR.index("async function vaciarCola")
    cola = REPORTAR[inicio:REPORTAR.index("function enviarPendientes")]
    assert "enviar(pendiente)" in cola  # la cola siempre manda a /reportes


def test_piloto_js_no_inserta_html_y_pide_las_10_frases_del_sus():
    assert "innerHTML" not in PILOTO
    assert PILOTO.count("aplicación") >= 5 and "'/piloto/resultados'" in PILOTO
    frases = PILOTO[PILOTO.index("const FRASES"):PILOTO.index("];")]
    assert frases.count("',") + frases.count("'.\n") >= 10


def test_el_service_worker_guarda_piloto_js():
    sw = (PWA / "sw.js").read_text(encoding="utf-8")
    assert "'piloto.js'" in sw and "patitas-pwa-v8" in sw
