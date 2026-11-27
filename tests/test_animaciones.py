"""Animaciones Lottie decorativas (#467): archivos livianos servidos desde el propio sitio, carga
perezosa, respaldo con movimiento reducido, CSP sin cambios y créditos documentados."""
import json
from pathlib import Path

import pytest

from tests.test_inicio import c  # noqa: F401  (fixture de la app en memoria)

RAIZ = Path(__file__).resolve().parents[1]
LOTTIE = RAIZ / "app" / "diseno" / "lottie"
NOMBRES = ("perro-caminando", "perrito-saltando", "gatos-jugando", "huellas-cargando")


@pytest.mark.parametrize("nombre", NOMBRES)
def test_cada_animacion_es_liviana_y_se_sirve_desde_el_sitio(c, nombre):  # noqa: F811
    archivo = LOTTIE / f"{nombre}.json"
    assert archivo.stat().st_size < 300_000, nombre
    datos = json.loads(archivo.read_text(encoding="utf-8"))
    assert datos["layers"] and not [a for a in datos.get("assets", []) if "p" in a]  # sin imágenes
    r = c.get(f"/diseno/lottie/{nombre}.json")
    assert r.status_code == 200 and r.headers["content-type"].startswith("application/json")


def test_reproductor_liviano_con_licencia_y_sin_eval(c):  # noqa: F811
    carpeta = RAIZ / "app" / "diseno" / "vendor" / "lottie"
    assert "MIT" in (carpeta / "LICENSE.md").read_text(encoding="utf-8")
    js = (carpeta / "lottie_light.min.js").read_text(encoding="utf-8")
    assert "new Function" not in js and "eval(" not in js  # la CSP no necesita 'unsafe-eval'
    assert c.get("/diseno/vendor/lottie/lottie_light.min.js").status_code == 200


def test_la_csp_no_admite_dominios_externos(c):  # noqa: F811
    for ruta in ("/", "/app/"):
        politica = c.get(ruta).headers["content-security-policy"]
        directivas = dict(d.strip().split(" ", 1) for d in politica.split(";") if d.strip())
        assert directivas["script-src"] == "'self'" and directivas["connect-src"] == "'self'"
        assert "unsafe-eval" not in politica and "lottiefiles" not in politica


def test_carga_perezosa_con_respaldo_y_movimiento_reducido():
    js = (RAIZ / "app" / "diseno" / "animaciones.js").read_text(encoding="utf-8")
    assert "new IntersectionObserver" in js and "anim.pause()" in js
    assert "prefers-reduced-motion: reduce" in js and "if (!reducido.matches) vigia.observe" in js
    inicio = (RAIZ / "app" / "inicio" / "index.html").read_text(encoding="utf-8")
    assert "data-lottie" not in inicio and "animaciones.js" not in inicio  # #474: caminantes en SVG
    pwa = (RAIZ / "app" / "pwa" / "index.html").read_text(encoding="utf-8")
    huellas = '<span class="consultando-huellas" data-lottie="huellas-cargando" aria-hidden="true">'
    assert huellas in pwa
    assert "Consultando tu reporte…" in pwa  # el texto sigue para el lector de pantalla


def test_creditos_de_las_animaciones():
    creditos = (RAIZ / "docs" / "CREDITOS-ANIMACIONES.md").read_text(encoding="utf-8")
    for nombre in NOMBRES:
        assert nombre in creditos, nombre
    assert "LottieFiles" in creditos and "licencia gratuita" in creditos
