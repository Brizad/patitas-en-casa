"""Tarea 6 (#459): ninguna página pública enlaza ni menciona el repositorio de GitHub.

Se revisa lo que sirve el sitio (inicio, app ciudadana, panel, manifest, documentación de la API)
y las fuentes de donde sale (app/inicio, app/pwa, panel/src y panel/index.html). El README, los
workflows y docs/ no son parte de la página y no se revisan aquí.
"""
from pathlib import Path

import pytest

from tests.test_inicio import c  # noqa: F401  (fixture de la app en memoria)

RAIZ = Path(__file__).resolve().parents[1]
PROHIBIDOS = ("github.com/brizad", "código abierto", "codigo abierto")
FUENTES = [RAIZ / "app" / "inicio", RAIZ / "app" / "pwa", RAIZ / "panel" / "src",
           RAIZ / "panel" / "index.html"]
EXTENSIONES = {".html", ".css", ".js", ".ts", ".tsx", ".webmanifest", ".json", ".svg"}


def _archivos():
    for fuente in FUENTES:
        if fuente.is_file():
            yield fuente
            continue
        for archivo in fuente.rglob("*"):
            if archivo.suffix in EXTENSIONES and "vendor" not in archivo.parts:
                yield archivo


@pytest.mark.parametrize("ruta", ["/", "/app/", "/app/manifest.webmanifest", "/panel/",
                                  "/docs", "/openapi.json"])
def test_las_paginas_publicas_no_mencionan_el_repositorio(c, ruta):  # noqa: F811
    respuesta = c.get(ruta)
    if respuesta.status_code == 404 and ruta == "/panel/":
        pytest.skip("el panel se compila aparte (npm run build)")
    texto = respuesta.text.lower()
    for prohibido in PROHIBIDOS:
        assert prohibido not in texto, (ruta, prohibido)


def test_las_fuentes_publicas_no_mencionan_el_repositorio():
    encontrados = []
    for archivo in _archivos():
        texto = archivo.read_text(encoding="utf-8", errors="ignore").lower()
        encontrados += [f"{archivo.relative_to(RAIZ)}: {p}" for p in PROHIBIDOS if p in texto]
    assert encontrados == []
