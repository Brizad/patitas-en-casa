"""Revisión periódica de rescates sin aceptar (HU-06, RF-23, #46).

La API la arranca al iniciar. La revisión hace consultas y envía correos (bloqueantes), así que
corre en un hilo para no detener las peticiones. Un error se registra y la vigilancia sigue.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

log = logging.getLogger(__name__)


async def repetir_cada(accion: Callable[[], object], cada_s: float, nombre: str) -> None:
    """Ejecuta «accion» cada «cada_s» segundos en un hilo, sin detener las peticiones. Un
    error se registra y la repetición sigue (base o SMTP caídos)."""
    while True:
        await asyncio.sleep(cada_s)
        try:
            await asyncio.to_thread(accion)
        except Exception:
            log.exception("Falló la tarea periódica «%s»; se reintenta.", nombre)


async def vigilar_escalamientos(escalar: Callable[[], object], cada_s: float) -> None:
    await repetir_cada(escalar, cada_s, "revisión de rescates sin aceptar")
