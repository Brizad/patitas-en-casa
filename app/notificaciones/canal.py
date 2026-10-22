"""Puerto de envío de avisos (#63). El procesador depende de este contrato, no del SMTP."""
from __future__ import annotations

from typing import Protocol


class EntregaFallida(Exception):
    """El canal no aceptó el mensaje. «permanente»: reintentar no ayudaría."""

    def __init__(self, motivo: str, *, permanente: bool = False) -> None:
        super().__init__(motivo)
        self.permanente = permanente


class CanalAviso(Protocol):
    def entregar(self, destinatario: str, mensaje: str) -> None:
        """Entrega o lanza EntregaFallida. Entregar al servidor no prueba que alguien leyó."""
        ...
