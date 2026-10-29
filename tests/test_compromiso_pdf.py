"""RF-29 (#85): compromiso de adopción en PDF, solo para adopciones aprobadas."""
import re

from app.documentos.pdf import generar_pdf
from tests.test_decision_adopcion import en_memoria, h, preparar


def test_el_pdf_es_valido_y_su_xref_apunta_a_cada_objeto():
    pdf = generar_pdf([("Título (prueba)", 18), "Ñandú con tilde: á é í ó ú"])
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF")
    inicio = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    assert pdf[inicio:inicio + 4] == b"xref"
    posiciones = [int(p) for p in re.findall(rb"(\d{10}) 00000 n", pdf)]
    for numero, posicion in enumerate(posiciones, start=1):
        assert pdf[posicion:].startswith(b"%d 0 obj" % numero)
    assert b"T\xedtulo \\(prueba\\)" in pdf  # cp1252 y paréntesis escapados
    assert "Ñandú".encode("cp1252") in pdf


def test_muchas_lineas_hacen_varias_paginas():
    pdf = generar_pdf([f"Línea {i}" for i in range(120)])
    assert b"/Count 3" in pdf


def test_compromiso_de_una_adopcion_aprobada():
    c = en_memoria()
    coord, _, ids = preparar(c)
    sid = ids["lau@correo.co"]
    ruta = f"/adopciones/solicitudes/{sid}/compromiso.pdf"
    assert c.get(ruta, headers=h(c, "lau@correo.co")).status_code == 409  # aún pendiente
    c.post(f"/refugio/solicitudes/{sid}/decision", json={"aprobar": True}, headers=coord)
    r = c.get(ruta, headers=h(c, "lau@correo.co"))
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert "attachment" in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF") and b"Canela" in r.content
    assert c.get(ruta, headers=coord).status_code == 200  # el refugio también lo imprime


def test_otro_adoptante_no_ve_el_compromiso():
    c = en_memoria()
    coord, _, ids = preparar(c)
    sid = ids["lau@correo.co"]
    c.post(f"/refugio/solicitudes/{sid}/decision", json={"aprobar": True}, headers=coord)
    ruta = f"/adopciones/solicitudes/{sid}/compromiso.pdf"
    assert c.get(ruta).status_code == 401
    assert c.get(ruta, headers=h(c, "ana@correo.co")).status_code == 404
