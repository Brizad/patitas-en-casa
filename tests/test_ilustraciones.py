"""Ilustraciones SVG originales del rediseño (#308): ícono de la app e íconos por rol.

Se protegen tres cosas: que sean SVG válidos y seguros (sin <script>, <style> ni recursos
externos: la CSP solo admite el propio servidor), que usen solo la paleta de DESIGN.md y que de
verdad se usen en la página de inicio y en el panel.
"""
import re
import xml.etree.ElementTree as ET
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
ROLES = ("ciudadano", "veterinario", "rescatista", "coordinador", "adoptante", "administrador",
         "alcaldia")
PALETA = {"#ffffeb", "#1a1a1a", "#f0d7ff", "#034f46", "#ffa946", "#e4e4d0", "#ffffff"}
ILUSTRACIONES = ("portada", "sin-reportes", "sin-rescates")  # parte 2
SVGS = ([RAIZ / "app" / "pwa" / "icono.svg"]
        + [RAIZ / "app" / "diseno" / "roles" / f"{r}.svg" for r in ROLES]
        + [RAIZ / "app" / "diseno" / "ilustraciones" / f"{i}.svg" for i in ILUSTRACIONES])


@pytest.fixture
def c():
    return TestClient(crear_app(
        RepositorioEnMemoria(), RepositorioCuposEnMemoria(Refugio("Refugio demo", 40)),
        repositorio_usuarios=RepositorioUsuariosEnMemoria(),
        emisor_tokens=EmisorTokens("secreto-de-pruebas-con-mas-de-32-caracteres")))


@pytest.mark.parametrize("svg", SVGS, ids=lambda p: p.stem)
def test_svg_valido_seguro_y_con_la_paleta(svg):
    texto = svg.read_text(encoding="utf-8")
    raiz = ET.fromstring(texto)  # XML bien formado
    assert raiz.tag.endswith("svg") and raiz.get("viewBox")
    etiquetas = {e.tag.split("}")[-1] for e in raiz.iter()}
    assert not etiquetas & {"script", "style", "image", "foreignObject", "use"}
    sin_xmlns = texto.replace('xmlns="http://www.w3.org/2000/svg"', "")
    assert "http" not in sin_xmlns and "href" not in sin_xmlns and " on" not in sin_xmlns
    colores = {c.lower() for c in re.findall(r'(?:fill|stroke)="(#[0-9a-fA-F]{6})"', texto)}
    assert colores and colores <= PALETA, colores - PALETA


def test_los_iconos_de_rol_se_sirven_como_svg(c):
    for rol in ROLES:
        r = c.get(f"/diseno/roles/{rol}.svg")
        assert r.status_code == 200 and r.headers["content-type"].startswith("image/svg+xml"), rol


def test_la_pagina_de_inicio_muestra_un_icono_por_rol(c):
    html = c.get("/").text
    css = (RAIZ / "app" / "inicio" / "inicio.css").read_text(encoding="utf-8")
    for rol in ROLES:
        assert f"rol-{rol} tarjeta" in html, rol  # #426: tarjeta del rol con su icono
        assert f"url(/diseno/roles/{rol}.svg)" in css, rol


def test_el_panel_muestra_el_icono_del_rol_en_la_cabecera():
    app = (RAIZ / "panel" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "/diseno/roles/${cuenta.rol}.svg" in app


def test_la_portada_tiene_su_dibujo_decorativo(c):
    # #328: la ilustración de la portada se cambió por el rastro de huellas (dibujado en línea).
    html = c.get("/").text
    assert re.search(r'<svg class="rastro"[^>]*aria-hidden="true"', html)
    assert "/diseno/ilustraciones/portada.svg" not in html


def test_los_estados_vacios_del_panel_tienen_ilustracion():
    src = RAIZ / "panel" / "src"
    for archivo, ilustracion in (("Cola.tsx", "sin-reportes"), ("Rescatista.tsx", "sin-rescates"),
                                 ("MisRescates.tsx", "sin-rescates")):
        codigo = (src / archivo).read_text(encoding="utf-8")
        assert f'src="/diseno/ilustraciones/{ilustracion}.svg" alt=""' in codigo, archivo


def test_el_service_worker_baja_el_icono_y_las_hojas_nuevas():
    # El ícono (icono.svg) y las hojas cambiaron: con otra versión, el teléfono reemplaza la
    # copia sin señal; con la misma, seguiría abriendo la interfaz vieja.
    sw = (RAIZ / "app" / "pwa" / "sw.js").read_text(encoding="utf-8")
    version = int(re.search(r"patitas-pwa-v(\d+)'", sw).group(1))
    assert version >= 10 and "'icono.svg'" in sw
