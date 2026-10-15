"""Revisión periódica de rescates sin aceptar (HU-06, RF-23, #46).

La API la arranca al iniciar. La revisión hace consultas y envía correos (bloqueantes), así que
corre en un hilo para no detener las peticiones. Un error se registra y la vigilancia sigue.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

log = logging.getLogger(__name__)


async def vigilar_escalamientos(escalar: Callable[[], object], cada_s: float) -> None:
    while True:
        await asyncio.sleep(cada_s)
        try:
            await asyncio.to_thread(escalar)
        except Exception:
            # La vigilancia no debe morir por un fallo puntual (base o SMTP caídos).
            log.exception("Falló la revisión de rescates sin aceptar; se reintenta.")
