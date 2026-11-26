"""Cambio 2 (#464): lo que ve el público se presenta como producto, sin menciones académicas.

Lo académico vive en README, docs/ y PLAN_CIERRE.md, que no son parte de la página.
"""
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.documentacion import DESCRIPCION, limpiar
from app.api.main import crear_app
from app.cupos.repositorio import RepositorioCuposEnMemoria
from app.dominio.modelos import Refugio
from app.reportes.repositorio import RepositorioEnMemoria
from app.seguridad.tokens import EmisorTokens
from app.usuarios.repositorio import RepositorioUsuariosEnMemoria
from tests.test_inicio import c  # noqa: F401  (fixture de la app en memoria)

RAIZ = Path(__file__).resolve().parents[1]
ACADEMICO = ("universidad", "pamplona", "ingeniería de software", "ingenieria de software",
             "proyecto integrador", "trabajo de grado")
PUBLICAS = ["/", "/app/", "/app/manifest.webmanifest", "/panel/", "/docs", "/openapi.json"]
# #470: nada técnico a la vista del público (la documentación de la API no se enlaza ni se abre).
TECNICO = ("documentación de la api", "documentacion de la api", "/docs", "swagger", "openapi")
PAGINAS = ["/", "/app/", "/app/manifest.webmanifest", "/panel/"]


def _app(docs_publicas=None):
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo Cúcuta", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(), docs_publicas=docs_publicas,
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


@pytest.mark.parametrize("ruta", PUBLICAS)
def test_ninguna_pagina_publica_tiene_menciones_academicas(c, ruta):  # noqa: F811
    respuesta = c.get(ruta)
    if respuesta.status_code == 404 and ruta == "/panel/":
        pytest.skip("el panel se compila aparte (npm run build)")
    texto = respuesta.text.lower()
    for palabra in ACADEMICO:
        assert palabra not in texto, (ruta, palabra)


@pytest.mark.parametrize("ruta", PAGINAS)
def test_ninguna_pagina_publica_menciona_la_documentacion_de_la_api(c, ruta):  # noqa: F811
    respuesta = c.get(ruta)
    if respuesta.status_code == 404 and ruta == "/panel/":
        pytest.skip("el panel se compila aparte (npm run build)")
    texto = respuesta.text.lower()
    for palabra in TECNICO:
        assert palabra not in texto, (ruta, palabra)


def test_la_documentacion_interactiva_esta_cerrada_por_defecto(monkeypatch):
    monkeypatch.delenv("PATITAS_DOCS_PUBLICAS", raising=False)
    cerrada = _app()
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        assert cerrada.get(ruta).status_code == 404, ruta
    assert cerrada.app.openapi()["info"]["title"] == "Patitas en Casa"  # sigue para uso interno
    monkeypatch.setenv("PATITAS_DOCS_PUBLICAS", "true")
    abierta = _app()
    for ruta in ("/docs", "/redoc", "/openapi.json"):
        assert abierta.get(ruta).status_code == 200, ruta


def test_las_fuentes_publicas_no_tienen_menciones_academicas():
    fuentes = [RAIZ / "app" / "inicio", RAIZ / "app" / "pwa", RAIZ / "panel" / "src"]
    archivos = [a for f in fuentes for a in f.rglob("*")
                if a.suffix in {".html", ".js", ".ts", ".tsx", ".css", ".webmanifest"}
                and "vendor" not in a.parts]
    archivos.append(RAIZ / "panel" / "index.html")
    encontrados = [f"{a.relative_to(RAIZ)}: {p}" for a in archivos
                   for p in ACADEMICO if p in a.read_text(encoding="utf-8").lower()]
    assert encontrados == []


def test_pie_con_la_columna_plataforma(c):  # noqa: F811
    html = c.get("/").text
    pie = html[html.index('<footer class="pie">'):]
    assert ">Plataforma</p>" in pie and ">Proyecto</p>" not in pie and ">Navegación</p>" in pie
    assert '<a href="/panel/#personal">Para refugios y su equipo</a>' in pie
    assert '<a href="/app/#instalar">Instalar la app</a>' in pie
    assert '<a href="#como">Cómo funciona</a>' in pie and "/docs" not in pie  # #470
    assert "Diseñado y desarrollado por" in pie and "Brayan David Amado Ramírez" in pie
    assert "© 2026 Patitas en Casa · Cúcuta, Colombia" in pie and "por Brayan Amado" in pie


def test_la_documentacion_de_la_api_no_cita_requisitos_ni_issues():
    abierta = _app(docs_publicas=True)  # solo se publica con PATITAS_DOCS_PUBLICAS=true
    esquema = abierta.get("/openapi.json").json()
    assert esquema["info"]["description"] == DESCRIPCION
    textos = re.findall(r'"(?:description|summary)":\s*"((?:[^"\\]|\\.)*)"',
                        abierta.get("/openapi.json").text)
    citas = [t for t in textos if re.search(r"\b(?:RNF|RF|RN|DT|HU|FPI)-\d|#\d+", t)]
    assert citas == []
    assert abierta.get("/docs").status_code == 200


@pytest.mark.parametrize(("antes", "despues"), [
    ("RF-27, RN-10: perfil lleno; una pendiente.", "Perfil lleno; una pendiente."),
    ("Sin datos del refugio ni de personas (RN-14).", "Sin datos del refugio ni de personas."),
    ("RF-27: aprobar (RN-05, RN-11; egreso RF-10) o rechazar.", "Aprobar (egreso) o rechazar."),
    ("Usuario = correo (DT-02).  DT-06: con fallos", "Usuario = correo. Con fallos"),
    ("#422: corrige la publicación.", "Corrige la publicación."),
    ("Texto normal: 300 KB y 10 s.", "Texto normal: 300 KB y 10 s."),
])
def test_limpiar_quita_solo_las_citas_internas(antes, despues):
    assert limpiar(antes) == despues


def test_instalar_la_app_desde_el_pie():
    app = (RAIZ / "app" / "pwa" / "app.js").read_text(encoding="utf-8")
    html = (RAIZ / "app" / "pwa" / "index.html").read_text(encoding="utf-8")
    assert "} else if (nombre === 'instalar') {" in app and "beforeinstallprompt" in app
    assert "pedidoInstalar.prompt();" in app  # solo con el toque de la persona
    assert '<div id="aviso-instalar" class="aviso aviso--amarillo" role="status" hidden>' in html
