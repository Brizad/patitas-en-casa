"""Fotos de los animales publicados para adopción (RF-25, #115).

¿Por qué en la base y no en una carpeta? En el plan gratis de Render el disco del servicio se
borra en cada despliegue: una carpeta perdería las fotos. PostgreSQL sí persiste, pero el plan
gratis tiene 1 GB, así que cada foto se limita a 300 KB (una foto de celular reducida).

Seguridad: el tipo se decide por los primeros bytes del archivo («número mágico»), no por el
nombre ni por lo que diga el navegador. Así nadie sube un HTML o un script con extensión .jpg.
"""
from __future__ import annotations

from typing import Protocol

MAX_BYTES = 300 * 1024
FIRMAS = {  # primeros bytes → tipo MIME
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}


class FotoInvalida(ValueError):
    pass


def tipo_de_imagen(datos: bytes) -> str:
    """Devuelve el tipo MIME si los bytes son JPEG, PNG o WebP; si no, FotoInvalida."""
    if len(datos) > MAX_BYTES:
        raise FotoInvalida(f"La foto pesa más de {MAX_BYTES // 1024} KB: redúcela.")
    for firma, tipo in FIRMAS.items():
        if datos.startswith(firma):
            return tipo
    if datos[:4] == b"RIFF" and datos[8:12] == b"WEBP":
        return "image/webp"
    raise FotoInvalida("Solo se aceptan fotos JPEG, PNG o WebP.")


class RepositorioFotos(Protocol):
    def guardar(self, animal_id: int, tipo: str, datos: bytes) -> None:
        """Una foto por animal: guardar otra la reemplaza."""
        ...

    def foto(self, animal_id: int) -> tuple[str, bytes] | None: ...

    def con_foto(self) -> set[int]: ...


class RepositorioFotosEnMemoria:
    def __init__(self) -> None:
        self._fotos: dict[int, tuple[str, bytes]] = {}

    def guardar(self, animal_id: int, tipo: str, datos: bytes) -> None:
        self._fotos[animal_id] = (tipo, datos)

    def foto(self, animal_id: int) -> tuple[str, bytes] | None:
        return self._fotos.get(animal_id)

    def con_foto(self) -> set[int]:
        return set(self._fotos)
