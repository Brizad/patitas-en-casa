"""Correos con diseño (#310): el mismo aviso de texto, también en HTML.

Sin red: la plantilla es una función pura; el SMTP y Mailjet se prueban con sus dobles.
"""
import json
import smtplib
from html.parser import HTMLParser

import pytest

from app.notificaciones.correo import NotificadorCorreo
from app.notificaciones.mailjet import NotificadorMailjet
from app.notificaciones.plantilla import componer

BASE = "https://patitas.prueba.local"
RESCATE = "Rescate Crítica F2HW5RTB en la comuna 6. Acéptalo en el panel."
CIUDADANO = "Patitas en Casa: tu reporte F2HW5RTB ya tiene rescatista en camino."
VACIOS = {"meta", "br", "img", "hr", "link", "input"}


class Estructura(HTMLParser):
    """Comprueba que cada etiqueta que abre también cierra, en orden."""

    def __init__(self):
        super().__init__()
        self.pila, self.errores, self.etiquetas, self.enlaces = [], [], [], []

    def handle_starttag(self, tag, attrs):
        self.etiquetas.append(tag)
        self.enlaces += [v for k, v in attrs if k in ("href", "src")]
        if tag not in VACIOS:
            self.pila.append(tag)

    def handle_endtag(self, tag):
        if not self.pila or self.pila.pop() != tag:
            self.errores.append(tag)


def analizar(html: str) -> Estructura:
    e = Estructura()
    e.feed(html)
    e.close()
    return e


@pytest.mark.parametrize("mensaje", [RESCATE, CIUDADANO, "Ocupación sobre el 90 % en Refugio"])
def test_html_bien_formado_sin_scripts_imagenes_ni_recursos_externos(mensaje):
    correo = componer(mensaje, BASE)
    e = analizar(correo.html)
    assert e.errores == [] and e.pila == []
    assert not set(e.etiquetas) & {"script", "img", "link", "style", "iframe", "form"}
    assert all(enlace.startswith(BASE + "/") for enlace in e.enlaces)  # solo el botón
    assert "max-width:600px" in correo.html and "Georgia" in correo.html
    assert "Arial" in correo.html and "Patitas en Casa · Cúcuta" in correo.html


def test_el_texto_plano_y_el_asunto_son_los_de_siempre():
    correo = componer(RESCATE, BASE)
    assert correo.texto == f"{RESCATE}\n\nMensaje automático de Patitas en Casa."
    assert correo.asunto == f"[Patitas en Casa] {RESCATE}"[:120]


def test_el_codigo_va_destacado_y_el_boton_depende_de_quien_lo_recibe():
    ciudadano = componer(CIUDADANO, BASE).html
    assert ">F2HW5RTB<" in ciudadano  # el código en su propio recuadro
    assert "Tu reporte F2HW5RTB" in ciudadano  # sin el prefijo y con mayúscula inicial
    assert f'href="{BASE}/app/#estado/F2HW5RTB"' in ciudadano
    assert "Ver el estado del reporte" in ciudadano
    personal = componer(RESCATE, BASE).html
    assert f'href="{BASE}/panel/"' in personal and "Abrir el panel" in personal
    sin_codigo = componer("Ocupación sobre el 90 % en Refugio", BASE).html
    assert "Código del reporte" not in sin_codigo


def test_escapa_todo_dato():
    correo = componer('Rescate <script>alert("x")</script> & <b>F2HW5RTB</b>', BASE)
    assert "<script>" not in correo.html and "<b>" not in correo.html
    assert "&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp;" in correo.html


def test_no_agrega_datos_que_no_trae_el_aviso():
    """RN-14: el HTML no inventa ubicación ni correos; solo lo que ya dice el texto."""
    correo = componer(CIUDADANO, BASE)
    assert "@" not in correo.html and "comuna" not in correo.html.lower()


class SMTPFalso:
    enviados: list = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, *args):
        pass

    def send_message(self, mensaje):
        SMTPFalso.enviados.append(mensaje)


def test_smtp_envia_multipart_con_texto_y_html(monkeypatch):
    SMTPFalso.enviados = []
    monkeypatch.setattr(smtplib, "SMTP", SMTPFalso)
    NotificadorCorreo("smtp.prueba.local", 587, "a@prueba.local", {},
                      url_publica=BASE).entregar("ana@rescate.co", RESCATE)
    (mensaje,) = SMTPFalso.enviados
    assert mensaje.get_content_type() == "multipart/alternative"
    texto = mensaje.get_body(("plain",)).get_content()
    assert texto.strip() == componer(RESCATE, BASE).texto
    assert "Abrir el panel" in mensaje.get_body(("html",)).get_content()


def test_mailjet_envia_text_part_y_html_part(monkeypatch):
    enviados = []

    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"Messages": [{"Status": "success"}]}).encode()

    def abrir(peticion, timeout):
        enviados.append(json.loads(peticion.data))
        return Respuesta()

    monkeypatch.setattr("urllib.request.urlopen", abrir)
    NotificadorMailjet("k", "s", "a@prueba.local", {}, url_publica=BASE).entregar(
        "ana@rescate.co", RESCATE)
    (cuerpo,) = enviados
    mensaje = cuerpo["Messages"][0]
    assert mensaje["TextPart"] == componer(RESCATE, BASE).texto
    assert mensaje["HTMLPart"] == componer(RESCATE, BASE).html
