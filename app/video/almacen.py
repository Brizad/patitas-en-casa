"""Videos en el disco temporal del servidor (#125). Adaptador de `AlmacenVideos`.

En Render gratis el disco se borra al reiniciar o al dormirse el servicio: por eso el video
solo vive aquí unos minutos, hasta que el trabajador local lo descarga. Si se pierde, el
trabajo queda «fallido» y manda el texto (falla segura).
"""
from __future__ import annotations

import contextlib
import secrets
from collections.abc import AsyncIterator
from pathlib import Path

from app import config

MAX_BYTES = config.VIDEO_MAX_MB * 1024 * 1024
# Firmas de los formatos que graba un celular: MP4/MOV (caja «ftyp» en el byte 4) y WebM.
WEBM = b"\x1a\x45\xdf\xa3"


class ArchivoInvalido(ValueError):
    pass


def es_video(inicio: bytes) -> bool:
    return inicio[4:8] == b"ftyp" or inicio.startswith(WEBM)


class AlmacenEnDisco:
    def __init__(self, directorio: str | Path) -> None:
        self._directorio = Path(directorio)
        self._directorio.mkdir(parents=True, exist_ok=True)

    async def guardar(self, trozos: AsyncIterator[bytes]) -> tuple[str, int]:
        """Escribe el video por partes (nunca entero en memoria: Render tiene 512 MB). Si pasa
        de 50 MB o no es un video, lo borra y lanza ArchivoInvalido."""
        ruta = self._directorio / f"{secrets.token_hex(16)}.video"
        tamano, inicio = 0, b""
        try:
            with ruta.open("wb") as archivo:
                async for trozo in trozos:
                    tamano += len(trozo)
                    if tamano > MAX_BYTES:
                        raise ArchivoInvalido(f"El video pasa de {config.VIDEO_MAX_MB} MB.")
                    if len(inicio) < 12:
                        inicio += trozo[:12]
                    archivo.write(trozo)
            if not es_video(inicio):
                raise ArchivoInvalido("El archivo no es un video MP4, MOV o WebM.")
        except BaseException:
            self.borrar(str(ruta))
            raise
        return str(ruta), tamano

    def existe(self, ruta: str) -> bool:
        return Path(ruta).is_file()

    def borrar(self, ruta: str) -> None:
        with contextlib.suppress(FileNotFoundError):
            Path(ruta).unlink()
