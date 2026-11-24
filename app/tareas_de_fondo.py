"""Tareas de fondo que solo consultan la base cuando hay trabajo (#390).

Neon descuenta cada minuto que la base está despierta y solo la suspende tras 5 minutos sin
consultas. Antes cada tarea consultaba cada 15 o 60 s aunque no hubiera nada que hacer, así que
la base nunca dormía. Ahora cada revisión dice cuándo hace falta la siguiente:

- un número: «vuelve en tantos segundos» (queda trabajo: un rescate por vencer, un video en curso);
- None: «no hay trabajo». La tarea duerme hasta que la despierten o, si tiene reposo creciente
  (los avisos), vuelve con una espera que se duplica hasta un tope.

Toda petición que cambia datos despierta las tareas (app/api/middlewares.py): en ese momento la
base ya está despierta por la propia petición, así que revisar entonces no cuesta minutos extra.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Reposo:
    """Espera que empieza en «inicial_s» y se duplica en cada revisión sin trabajo, hasta
    «maximo_s»."""
    inicial_s: float
    maximo_s: float

    def siguiente(self, actual: float) -> float:
        return min(actual * 2, self.maximo_s)


class TareaDeFondo:
    def __init__(self, nombre: str, revisar: Callable[[], float | None], *,
                 reposo: Reposo | None = None, tras_error: Reposo | None = None) -> None:
        self.nombre = nombre
        self._revisar = revisar
        self._reposo = reposo  # None: sin trabajo, duerme hasta que la despierten
        self._tras_error = tras_error or Reposo(60, 1800)
        self._bucle: asyncio.AbstractEventLoop | None = None
        self._evento: asyncio.Event | None = None
        self.esperas: list[float | None] = []  # lo que decidió esperar tras cada revisión

    def despertar(self) -> None:
        """Pide una revisión ya. Sirve desde cualquier hilo; si la tarea no corre, no hace nada."""
        bucle, evento = self._bucle, self._evento
        if bucle is None or evento is None:
            return
        try:
            bucle.call_soon_threadsafe(evento.set)
        except RuntimeError:  # el bucle ya se cerró (la app se está apagando)
            pass

    async def correr(self) -> None:
        """Revisa al arrancar (puede haber trabajo de antes del reinicio) y luego solo cuando
        la revisión lo pide, cuando la despiertan o cuando vence el reposo."""
        self._bucle, self._evento = asyncio.get_running_loop(), asyncio.Event()
        reposo = self._reposo.inicial_s if self._reposo else None
        error = self._tras_error.inicial_s
        while True:
            self._evento.clear()  # lo que llegue durante la revisión provoca otra enseguida
            try:
                pedido = await asyncio.to_thread(self._revisar)
                error = self._tras_error.inicial_s
            except Exception:
                log.exception("Falló la tarea de fondo «%s»; se reintenta en %s s.",
                              self.nombre, error)
                pedido, error = error, self._tras_error.siguiente(error)
            if pedido is not None:
                espera = max(0.0, pedido)
                reposo = self._reposo.inicial_s if self._reposo else None
            elif self._reposo is not None and reposo is not None:
                espera, reposo = reposo, self._reposo.siguiente(reposo)
            else:
                espera = None
            self.esperas.append(espera)
            if await self._esperar(espera) and self._reposo is not None:
                reposo = self._reposo.inicial_s  # hubo actividad: vuelve a mirar seguido

    async def _esperar(self, segundos: float | None) -> bool:
        """True si la despertaron; False si venció la espera. None: sin límite."""
        evento = self._evento
        if evento is None:
            return False
        try:
            await asyncio.wait_for(evento.wait(), timeout=segundos)
            return True
        except TimeoutError:
            return False
