"""Procesador de avisos (#63, outbox): toma los avisos pendientes y los envía.

Garantía: **al menos una vez**. Si el proceso se detiene después de que el servidor de correo
aceptó un aviso y antes de marcarlo enviado, el reclamo vence y el aviso se vuelve a enviar: el
rescatista podría recibirlo dos veces. Se prefiere eso a perder un aviso de un caso crítico.
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app import config
from app.avisos.repositorio import RepositorioAvisos
from app.notificaciones.correo import EntregaFallida

log = logging.getLogger(__name__)

ESPERA_MAXIMA = timedelta(hours=1)


class ProcesadorAvisos:
    def __init__(self, repositorio: RepositorioAvisos, canal, *,
                 reloj: Callable[[], datetime] | None = None,
                 max_intentos: int = config.MAX_INTENTOS_AVISO,
                 espera_base_s: float = config.ESPERA_BASE_AVISO_S,
                 vencimiento_s: float = config.VENCIMIENTO_RECLAMO_AVISO_S,
                 limite: int = 20) -> None:
        self._repo = repositorio
        # Los canales nuevos informan fallas con entregar(); uno antiguo solo tiene enviar().
        self._entregar = getattr(canal, "entregar", None) or canal.enviar
        self._reloj = reloj or (lambda: datetime.now(UTC))
        self._max_intentos = max_intentos
        self._espera_base = timedelta(seconds=espera_base_s)
        self._vencimiento = timedelta(seconds=vencimiento_s)
        self._limite = limite

    def _proximo(self, intentos: int, ahora: datetime) -> datetime:
        """Espera exponencial: 1, 2, 4… veces la base, hasta una hora."""
        return ahora + min(self._espera_base * 2 ** (intentos - 1), ESPERA_MAXIMA)

    def procesar(self) -> dict[str, int]:
        cuenta = {"enviados": 0, "reintentos": 0, "fallidos": 0}
        for aviso in self._repo.reclamar(self._reloj(), self._limite, self._vencimiento):
            try:
                self._entregar(aviso.destinatario, aviso.mensaje)
            except Exception as error:
                motivo = str(error) if isinstance(error, EntregaFallida) else type(error).__name__
                permanente = isinstance(error, EntregaFallida) and error.permanente
                if permanente or aviso.intentos >= self._max_intentos:
                    self._repo.marcar_fallo(aviso.id, motivo, None)
                    cuenta["fallidos"] += 1
                    log.error("Aviso %s del reporte %s fallido tras %s intentos: %s",
                              aviso.id, aviso.reporte_codigo, aviso.intentos, motivo)
                else:
                    self._repo.marcar_fallo(aviso.id, motivo,
                                            self._proximo(aviso.intentos, self._reloj()))
                    cuenta["reintentos"] += 1
                continue
            self._repo.marcar_enviado(aviso.id, self._reloj())
            cuenta["enviados"] += 1
        return cuenta
