"""Videos en el disco temporal del servidor (#125). Adaptador de `AlmacenVideos`.

En Render gratis el disco se borra al reiniciar o al dormirse el servicio: por eso el video
solo vive aquí unos minutos, hasta que el trabajador local lo descarga. Si se pierde, el
trabajo queda «fallido» y manda el texto (falla segura).
"""
from __future__ import annotations

import asyncio
import contextlib
import secrets
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import Engine, Table, delete, select

from app import config
from app.bd.esquema import videos_trozos

MAX_BYTES = config.VIDEO_MAX_MB * 1024 * 1024
# Firmas de los formatos que graba un celular: MP4/MOV (caja «ftyp» en el byte 4) y WebM.
WEBM = b"\x1a\x45\xdf\xa3"


class ArchivoInvalido(ValueError):
    pass


def es_video(inicio: bytes) -> bool:
    return inicio[4:8] == b"ftyp" or inicio.startswith(WEBM)


def _limite_texto(max_bytes: int) -> str:
    megas = max_bytes / (1024 * 1024)
    return f"El video pasa de {megas:g} MB."


class AlmacenEnDisco:
    """`max_bytes` y `extension` permiten un segundo almacén para la vista previa (#214)."""

    def __init__(self, directorio: str | Path, max_bytes: int | None = None,
                 extension: str = ".video") -> None:
        self._tope, self._extension = max_bytes, extension
        self._directorio = Path(directorio)
        self._directorio.mkdir(parents=True, exist_ok=True)

    async def guardar(self, trozos: AsyncIterator[bytes]) -> tuple[str, int]:
        """Escribe el video por partes (nunca entero en memoria: Render tiene 512 MB). Si pasa
        de 50 MB o no es un video, lo borra y lanza ArchivoInvalido."""
        ruta = self._directorio / f"{secrets.token_hex(16)}{self._extension}"
        tamano, inicio = 0, b""
        try:
            with ruta.open("wb") as archivo:
                async for trozo in trozos:
                    tamano += len(trozo)
                    if tamano > (self._tope or MAX_BYTES):
                        raise ArchivoInvalido(_limite_texto(self._tope or MAX_BYTES))
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

    def leer(self, ruta: str) -> Iterator[bytes]:
        with Path(ruta).open("rb") as archivo:
            while trozo := archivo.read(config.TROZO_VIDEO_BYTES):
                yield trozo

    def purgar_antes_de(self, limite: datetime) -> int:
        return 0  # el disco temporal ya se borra solo al reiniciar

    def borrar(self, ruta: str) -> None:
        with contextlib.suppress(FileNotFoundError):
            Path(ruta).unlink()


class AlmacenEnPostgres:
    """El video en trozos de 1 MB dentro de PostgreSQL (#188): sobrevive al reinicio de Render.

    Nunca se junta el video entero en memoria: cada trozo se escribe y se suelta. Se borra al
    terminar el análisis (ServicioVideo) o, si quedó huérfano, a las 6 horas (`purgar_antes_de`).
    """

    def __init__(self, motor: Engine, tabla: Table = videos_trozos,
                 max_bytes: int | None = None) -> None:
        self._motor, self._tabla, self._tope = motor, tabla, max_bytes

    async def guardar(self, trozos: AsyncIterator[bytes]) -> tuple[str, int]:
        ruta = secrets.token_hex(16)
        grande = config.TROZO_VIDEO_BYTES
        tamano, orden, inicio, pendiente = 0, 0, b"", bytearray()
        try:
            async for trozo in trozos:
                tamano += len(trozo)
                if tamano > (self._tope or MAX_BYTES):
                    raise ArchivoInvalido(_limite_texto(self._tope or MAX_BYTES))
                if len(inicio) < 12:
                    inicio = (inicio + trozo)[:12]
                pendiente += trozo
                while len(pendiente) >= grande:
                    await asyncio.to_thread(self._insertar, ruta, orden, bytes(pendiente[:grande]))
                    del pendiente[:grande]
                    orden += 1
            if not es_video(inicio):
                raise ArchivoInvalido("El archivo no es un video MP4, MOV o WebM.")
            if pendiente:
                await asyncio.to_thread(self._insertar, ruta, orden, bytes(pendiente))
        except BaseException:
            self.borrar(ruta)
            raise
        return ruta, tamano

    def _insertar(self, ruta: str, orden: int, datos: bytes) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(self._tabla.insert().values(
                ruta=ruta, orden=orden, datos=datos, creado_en=datetime.now(UTC)))

    def existe(self, ruta: str) -> bool:
        with self._motor.connect() as conexion:
            return conexion.execute(
                select(self._tabla.c.orden).where(self._tabla.c.ruta == ruta).limit(1)
            ).first() is not None

    def leer(self, ruta: str) -> Iterator[bytes]:
        """Un trozo por consulta: en memoria nunca hay más de 1 MB."""
        orden = 0
        while True:
            with self._motor.connect() as conexion:
                fila = conexion.execute(select(self._tabla.c.datos).where(
                    self._tabla.c.ruta == ruta, self._tabla.c.orden == orden)).first()
            if fila is None:
                return
            yield bytes(fila[0])
            orden += 1

    def borrar(self, ruta: str) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(delete(self._tabla).where(self._tabla.c.ruta == ruta))

    def purgar_antes_de(self, limite: datetime) -> int:
        """Trozos huérfanos (una subida cortada, un trabajo que ya no existe)."""
        with self._motor.begin() as conexion:
            return conexion.execute(
                delete(self._tabla).where(self._tabla.c.creado_en < limite)).rowcount
