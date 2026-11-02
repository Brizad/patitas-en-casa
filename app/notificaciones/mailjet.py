"""Envío de avisos por la API HTTPS de Mailjet (P-08).

Render gratis bloquea los puertos SMTP (25, 465 y 587); HTTPS (443) sí está abierto. Cumple el
mismo contrato que NotificadorCorreo (entregar/enviar), así que el outbox y los reintentos de
#63 no cambian. Solo usa la biblioteca estándar.
"""
from __future__ import annotations

import base64
import json
import logging
import urllib.error
import urllib.request

from app.notificaciones.canal import EntregaFallida

log = logging.getLogger(__name__)

URL_MAILJET = "https://api.mailjet.com/v3.1/send"
TIEMPO_MAXIMO_S = 10
LARGO_MAXIMO_ASUNTO = 120
# Un 4xx casi siempre es un mensaje que Mailjet rechaza: reintentar no ayuda. Estos sí se
# pueden arreglar (clave mal puesta, cuenta por validar) o pasan solos (límite de velocidad).
CODIGOS_REINTENTABLES = {401, 403, 408, 429}


class NotificadorMailjet:
    def __init__(self, api_key: str, secret_key: str, remitente: str,
                 grupos: dict[str, list[str]], url: str = URL_MAILJET) -> None:
        self._autorizacion = "Basic " + base64.b64encode(
            f"{api_key}:{secret_key}".encode()).decode()
        self._remitente = remitente
        self._grupos = grupos
        self._url = url

    def entregar(self, destinatario: str, mensaje: str) -> None:
        """Lanza EntregaFallida si Mailjet no acepta el mensaje."""
        correos = [destinatario] if "@" in destinatario else self._grupos.get(destinatario, [])
        if not correos:
            raise EntregaFallida(f"No hay correos configurados para {destinatario}.",
                                 permanente=True)
        cuerpo = json.dumps({"Messages": [{
            "From": {"Email": self._remitente, "Name": "Patitas en Casa"},
            "To": [{"Email": c} for c in correos],
            "Subject": f"[Patitas en Casa] {mensaje}"[:LARGO_MAXIMO_ASUNTO],
            "TextPart": f"{mensaje}\n\nMensaje automático de Patitas en Casa.",
        }]}).encode()
        peticion = urllib.request.Request(
            self._url, data=cuerpo, method="POST",
            headers={"Content-Type": "application/json", "Authorization": self._autorizacion})
        try:
            with urllib.request.urlopen(peticion, timeout=TIEMPO_MAXIMO_S) as respuesta:
                datos = json.loads(respuesta.read() or b"{}")
        except urllib.error.HTTPError as error:
            permanente = 400 <= error.code < 500 and error.code not in CODIGOS_REINTENTABLES
            raise EntregaFallida(f"Mailjet: HTTP {error.code}", permanente=permanente) from error
        except (urllib.error.URLError, OSError, ValueError) as error:
            # Solo el tipo de error: el texto podría incluir la dirección o la cuenta.
            raise EntregaFallida(f"Mailjet: {type(error).__name__}") from error
        estados = [m.get("Status") for m in datos.get("Messages", [])]
        if not estados or any(e != "success" for e in estados):
            raise EntregaFallida("Mailjet: respuesta sin success", permanente=True)

    def enviar(self, destinatario: str, mensaje: str) -> None:
        """Como entregar(), pero la falla queda en el log y no se propaga."""
        try:
            self.entregar(destinatario, mensaje)
        except EntregaFallida as error:
            nivel = logging.WARNING if error.permanente else logging.ERROR
            log.log(nivel, "No se pudo enviar la notificación a %s (%s): %s",
                    destinatario, error, mensaje)
