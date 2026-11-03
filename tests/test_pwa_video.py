"""#212: reglas del video en la PWA (RN-01: 60 s y 50 MB) y la grabadora dentro de la página.

La lógica pura está en app/pwa/video.js y se prueba con Node; el resto se revisa leyendo el
código y el HTML (la CSP no admite recursos externos ni innerHTML con datos).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

CARPETA_PWA = Path(__file__).resolve().parents[1] / "app" / "pwa"
NODE = shutil.which("node")
MB = 1024 * 1024
necesita_node = pytest.mark.skipif(NODE is None, reason="Node no está instalado")


def _evaluar(expresion: str):
    codigo = (f"const v = require({json.dumps((CARPETA_PWA / 'video.js').as_posix())});"
              f"console.log(JSON.stringify({expresion}));")
    salida = subprocess.run([NODE, "-e", codigo], capture_output=True, text=True,
                            encoding="utf-8", check=True)
    return json.loads(salida.stdout)


@necesita_node
@pytest.mark.parametrize("segundos, bytes_, texto", [
    (60, 50 * MB, ""),
    (1, 1, ""),
    (60.4, 10 * MB, "dura 60 s"),
    (61, 10 * MB, "máximo es 60 s"),
    (30, 50 * MB + 1, "máximo es 50 MB"),
    (30, 0, "vacío"),
    (None, 5 * MB, "No pudimos leer"),
])
def test_validar_video_aplica_rn01(segundos, bytes_, texto):
    argumento = "null" if segundos is None else str(segundos)
    mensaje = _evaluar(f"v.validarVideo({argumento}, {bytes_})")
    if texto:
        assert texto in mensaje
    else:
        assert mensaje == ""


@necesita_node
def test_validar_video_rechaza_duracion_infinita():
    assert "No pudimos leer" in _evaluar("v.validarVideo(Infinity, 5 * 1024 * 1024)")


@necesita_node
def test_formato_del_contador():
    assert _evaluar("[0, 5.9, 59, 60, 61].map(v.formatoTiempo)") == [
        "0:00", "0:05", "0:59", "1:00", "1:01"]


def test_la_pwa_ofrece_grabar_y_elegir_de_la_galeria():
    html = (CARPETA_PWA / "index.html").read_text(encoding="utf-8")
    assert "Grabar video" in html and "Elegir de la galería" in html
    assert 'src="video.js"' in html and html.index("video.js") < html.index("reportar.js")
    galeria = re.search(r'<input[^>]*id="video"[^>]*>', html).group(0)
    assert 'accept="video/' in galeria and "capture" not in galeria
    respaldo = re.search(r'<input[^>]*id="video-camara"[^>]*>', html).group(0)
    assert 'accept="video/*"' in respaldo and 'capture="environment"' in respaldo
    assert 'id="detener-video"' in html and 'id="repetir-video"' in html


def test_la_grabadora_respeta_los_limites_y_la_csp():
    js = (CARPETA_PWA / "reportar.js").read_text(encoding="utf-8")
    assert "innerHTML" not in js
    assert "MediaRecorder" in js and "environment" in js
    assert "audio: false" in js  # sin micrófono: la Permissions-Policy lo bloquea
    assert "MAX_SEGUNDOS" in js and "validarVideo" in js
    assert not re.search(r"https?://", (CARPETA_PWA / "video.js").read_text(encoding="utf-8"))


def test_el_service_worker_guarda_video_js():
    assert "'video.js'" in (CARPETA_PWA / "sw.js").read_text(encoding="utf-8")
