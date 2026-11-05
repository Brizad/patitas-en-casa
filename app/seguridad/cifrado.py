"""Cifrado de datos personales en reposo (RNF-08, RF-18, #111).

El contacto opcional del ciudadano (correo o teléfono) se guarda cifrado con AES-256-GCM:
quien lea la base (una copia de seguridad, un error de permisos) ve texto ilegible. La clave
sale de PATITAS_CLAVE_DATOS (Render la genera al azar con generateValue); nunca está en el
código ni en la base. GCM además detecta si alguien alteró el texto cifrado.

Formato guardado: base64(nonce de 12 bytes + texto cifrado con su etiqueta).

A-09 (#284): la clave v1 sale de un SHA-256 de PATITAS_CLAVE_DATOS, suficiente con una clave
al azar como la de Render. Si algún día la escribe una persona, PATITAS_CLAVE_KDF=scrypt cifra
lo nuevo con una clave derivada por scrypt (lento a propósito: cada intento de adivinarla
cuesta) y lo marca con «v2:». Lo viejo se sigue leyendo con la clave v1, y los dos formatos se
leen siempre: apagar el ajuste no deja nada ilegible.
"""
from __future__ import annotations

import base64
import hashlib
import os
from functools import cached_property

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

PREFIJO_AVISO = "cifrado:"  # destinatario de un aviso que se descifra solo al enviarlo
PREFIJO_V2 = "v2:"  # A-09: cifrado con la clave derivada por scrypt
# La sal es fija: la clave ya es única de cada despliegue; la sal solo separa este uso de otros.
SAL_V2 = b"patitas-en-casa/clave-datos/v2"
KDF_DISPONIBLES = ("sha256", "scrypt")


class Cifrador:
    def __init__(self, clave: str, kdf: str = "sha256") -> None:
        if len(clave) < 32:
            raise ValueError("La clave de datos debe tener al menos 32 caracteres.")
        if kdf not in KDF_DISPONIBLES:
            raise ValueError(f"PATITAS_CLAVE_KDF debe ser uno de {KDF_DISPONIBLES}.")
        self._clave = clave.encode()
        self._kdf = kdf
        # SHA-256 convierte cualquier texto largo en exactamente 32 bytes = AES-256.
        self._aes = AESGCM(hashlib.sha256(self._clave).digest())

    @cached_property
    def _aes_v2(self) -> AESGCM:
        """Se deriva una sola vez y solo si hace falta (~0,1 s y 16 MB de memoria)."""
        return AESGCM(Scrypt(salt=SAL_V2, length=32, n=2**14, r=8, p=1).derive(self._clave))

    def cifrar(self, texto: str) -> str:
        nonce = os.urandom(12)  # nunca se repite: dos cifrados del mismo texto se ven distintos
        aes, prefijo = (self._aes_v2, PREFIJO_V2) if self._kdf == "scrypt" else (self._aes, "")
        return prefijo + base64.b64encode(nonce + aes.encrypt(nonce, texto.encode(), None)).decode()

    def descifrar(self, guardado: str) -> str:
        aes = self._aes
        if guardado.startswith(PREFIJO_V2):
            aes, guardado = self._aes_v2, guardado.removeprefix(PREFIJO_V2)
        datos = base64.b64decode(guardado)
        return aes.decrypt(datos[:12], datos[12:], None).decode()


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
