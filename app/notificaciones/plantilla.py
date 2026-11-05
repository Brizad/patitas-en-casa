"""Correo con diseño (#310): el mismo aviso de texto, también en HTML con el estilo de DESIGN.md.

Reglas de correo (los clientes ignoran hojas externas y muchos el <style>): tablas y estilos en
línea, 600 px de ancho máximo, fuentes de respaldo (Georgia en el título, Arial/Helvetica en el
texto), sin JavaScript, sin imágenes ni píxeles de rastreo. El HTML se arma con el **mismo texto**
del aviso: no agrega datos (RN-14) y todo pasa por html.escape. El texto plano y el asunto son
los de siempre; el correo sale como multipart/alternative con los dos.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass

URL_PUBLICA = "https://patitas-en-casa-pnnk.onrender.com"
LARGO_MAXIMO_ASUNTO = 120
PIE_TEXTO = "Mensaje automático de Patitas en Casa."
PREFIJO_CIUDADANO = "Patitas en Casa:"  # los avisos al ciudadano y al adoptante empiezan así
CODIGO = re.compile(r"\b[A-Z0-9]{8}\b")  # el código de seguimiento (app/reportes/servicio.py)

# Paleta de DESIGN.md (los correos no leen las variables CSS del sitio).
TINTA, CREMA, LAVANDA, PIEDRA, SUAVE, BLANCO = (
    "#1a1a1a", "#ffffeb", "#f0d7ff", "#e4e4d0", "#5c5c54", "#ffffff")
SERIF = "Georgia,'Times New Roman',serif"
SANS = "Arial,Helvetica,sans-serif"


@dataclass(frozen=True)
class Correo:
    asunto: str
    texto: str
    html: str


def componer(mensaje: str, url_publica: str = URL_PUBLICA) -> Correo:
    asunto = f"[Patitas en Casa] {mensaje}"[:LARGO_MAXIMO_ASUNTO]
    return Correo(asunto, f"{mensaje}\n\n{PIE_TEXTO}", _html(mensaje, asunto, url_publica))


def _boton(mensaje: str, codigo: str | None, base: str) -> tuple[str, str]:
    """El ciudadano va a su seguimiento (solo código y pasos, RN-14); el personal, al panel."""
    if mensaje.startswith(PREFIJO_CIUDADANO):
        if codigo:
            return "Ver el estado del reporte", f"{base}/app/#estado/{codigo}"
        return "Entrar a Patitas en Casa", f"{base}/panel/"
    return "Abrir el panel", f"{base}/panel/"


def _html(mensaje: str, asunto: str, url_publica: str) -> str:
    e = html.escape
    encontrado = CODIGO.search(mensaje)
    codigo = encontrado.group(0) if encontrado else None
    etiqueta, enlace = _boton(mensaje, codigo, url_publica.rstrip("/"))
    frase = mensaje.removeprefix(PREFIJO_CIUDADANO).strip()  # la marca ya va en la cabecera
    cuerpo = e(frase[:1].upper() + frase[1:]).replace("\n", "<br>")
    recuadro = "" if codigo is None else (
        f'<tr><td style="padding:0 32px 24px">'
        f'<p style="margin:0 0 8px;font:700 12px {SANS};letter-spacing:1px;color:{SUAVE}">'
        f'Código del reporte</p>'
        f'<p style="margin:0;display:inline-block;padding:12px 20px;background:{LAVANDA};'
        f'border:2px solid {TINTA};border-radius:12px;font:700 24px \'Courier New\',monospace;'
        f'letter-spacing:3px;color:{TINTA}">{e(codigo)}</p></td></tr>')
    return (
        '<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<meta name="color-scheme" content="light"><title>{e(asunto)}</title></head>'
        f'<body style="margin:0;padding:0;background:{CREMA}">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="background:{CREMA}"><tr><td align="center" style="padding:24px 12px">'
        f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
        f'style="max-width:600px;background:{BLANCO};border:2px solid {TINTA};border-radius:24px">'
        f'<tr><td style="padding:24px 32px;border-bottom:2px solid {PIEDRA};'
        f'font:400 26px {SERIF};color:{TINTA}">Patitas en Casa</td></tr>'
        f'<tr><td style="padding:32px 32px 24px;font:400 18px/1.5 {SANS};color:{TINTA}">'
        f'{cuerpo}</td></tr>{recuadro}'
        f'<tr><td style="padding:0 32px 32px"><table role="presentation" cellpadding="0" '
        f'cellspacing="0" border="0"><tr><td style="background:{LAVANDA};border:2px solid {TINTA};'
        f'border-radius:12px"><a href="{e(enlace)}" style="display:inline-block;padding:14px 24px;'
        f'font:700 16px {SANS};color:{TINTA};text-decoration:none">{e(etiqueta)}</a>'
        f'</td></tr></table></td></tr>'
        f'<tr><td style="padding:20px 32px;background:{TINTA};border-radius:0 0 22px 22px;'
        f'font:400 14px/1.5 {SANS};color:{CREMA}">Patitas en Casa · Cúcuta<br>{e(PIE_TEXTO)}'
        '</td></tr></table></td></tr></table></body></html>')
