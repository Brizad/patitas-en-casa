"""Adaptadores de la interfaz Notificador (DT-03, HU-06).

- NotificadorCorreo: envía un correo por SMTP a un grupo (por ejemplo, "coordinadores") o,
  si el destinatario es un correo, a esa persona (alertas a rescatistas, HU-06).
- NotificadorRegistro: escribe la alerta en el log; se usa si no hay SMTP configurado.

Una falla del correo nunca deshace el ingreso que la causó: se registra en el log.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.ajustes import AjustesCorreo, ConfiguracionIncompleta

log = logging.getLogger(__name__)

TIEMPO_MAXIMO_SMTP_S = 10
LARGO_MAXIMO_ASUNTO = 120


class NotificadorRegistro:
    def enviar(self, destinatario: str, mensaje: str) -> None:
        log.warning("Notificación para %s: %s", destinatario, mensaje)


class NotificadorCorreo:
    def __init__(self, host: str, puerto: int, remitente: str, grupos: dict[str, list[str]],
                 usuario: str | None = None, contrasena: str | None = None,
                 starttls: bool = True) -> None:
        self._host = host
        self._puerto = puerto
        self._remitente = remitente
        self._grupos = grupos
        self._usuario = usuario
        self._contrasena = contrasena
        self._starttls = starttls

    def enviar(self, destinatario: str, mensaje: str) -> None:
        # HU-06: un destinatario con @ es una persona (rescatista); si no, es un grupo.
        correos = [destinatario] if "@" in destinatario else self._grupos.get(destinatario, [])
        if not correos:
            log.warning("No hay correos configurados para %s; alerta no enviada: %s",
                        destinatario, mensaje)
            return
        correo = EmailMessage()
        correo["From"] = self._remitente
        correo["To"] = ", ".join(correos)
        correo["Subject"] = f"[Patitas en Casa] {mensaje}"[:LARGO_MAXIMO_ASUNTO]
        correo.set_content(f"{mensaje}\n\nMensaje automático de Patitas en Casa.")
        try:
            with smtplib.SMTP(self._host, self._puerto, timeout=TIEMPO_MAXIMO_SMTP_S) as smtp:
                if self._starttls:
                    smtp.starttls()
                if self._usuario and self._contrasena:
                    smtp.login(self._usuario, self._contrasena)
                smtp.send_message(correo)
        except (smtplib.SMTPException, OSError) as error:
            log.error("No se pudo enviar la notificación a %s (%s): %s",
                      destinatario, type(error).__name__, mensaje)


def crear_notificador(ajustes: AjustesCorreo) -> NotificadorCorreo | NotificadorRegistro:
    if not ajustes.smtp_host:
        log.info("PATITAS_SMTP_HOST no configurado: las alertas irán al log.")
        return NotificadorRegistro()
    remitente = ajustes.smtp_remitente or ajustes.smtp_usuario
    if not remitente:
        raise ConfiguracionIncompleta(
            "Con PATITAS_SMTP_HOST hay que definir PATITAS_SMTP_REMITENTE o PATITAS_SMTP_USUARIO.")
    contrasena = ajustes.smtp_contrasena.get_secret_value() if ajustes.smtp_contrasena else None
    return NotificadorCorreo(
        host=ajustes.smtp_host, puerto=ajustes.smtp_port, remitente=remitente,
        grupos={"coordinadores": ajustes.coordinadores()}, usuario=ajustes.smtp_usuario,
        contrasena=contrasena, starttls=ajustes.smtp_starttls,
    )
