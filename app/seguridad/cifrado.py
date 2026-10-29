"""Cifrado de datos personales en reposo (RNF-08, RF-18, #111).

El contacto opcional del ciudadano (correo o teléfono) se guarda cifrado con AES-256-GCM:
quien lea la base (una copia de seguridad, un error de permisos) ve texto ilegible. La clave
sale de PATITAS_CLAVE_DATOS (Render la genera al azar con generateValue); nunca está en el
código ni en la base. GCM además detecta si alguien alteró el texto cifrado.

Formato guardado: base64(nonce de 12 bytes + texto cifrado con su etiqueta).
"""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

PREFIJO_AVISO = "cifrado:"  # destinatario de un aviso que se descifra solo al enviarlo


class Cifrador:
    def __init__(self, clave: str) -> None:
        if len(clave) < 32:
            raise ValueError("La clave de datos debe tener al menos 32 caracteres.")
        # SHA-256 convierte cualquier texto largo en exactamente 32 bytes = AES-256.
        self._aes = AESGCM(hashlib.sha256(clave.encode()).digest())

    def cifrar(self, texto: str) -> str:
        nonce = os.urandom(12)  # nunca se repite: dos cifrados del mismo texto se ven distintos
        return base64.b64encode(nonce + self._aes.encrypt(nonce, texto.encode(), None)).decode()

    def descifrar(self, guardado: str) -> str:
        datos = base64.b64decode(guardado)
        return self._aes.decrypt(datos[:12], datos[12:], None).decode()


class CanalConDescifrado:
    """Envuelve el canal de avisos: si el destinatario está cifrado, lo descifra justo antes
    de entregar. Así la tabla de avisos tampoco guarda el contacto en claro."""

    def __init__(self, canal, cifrador: Cifrador | None) -> None:
        self._canal = canal
        self._cifrador = cifrador
        self._entregar = getattr(canal, "entregar", None) or canal.enviar

    def entregar(self, destinatario: str, mensaje: str) -> None:
        if destinatario.startswith(PREFIJO_AVISO) and self._cifrador is not None:
            destinatario = self._cifrador.descifrar(destinatario.removeprefix(PREFIJO_AVISO))
        self._entregar(destinatario, mensaje)

    enviar = entregar
