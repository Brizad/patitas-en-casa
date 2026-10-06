"""Política de decisión del Motor de Triaje (RN-02, RN-03 y flujo E1 del UC-01)."""
from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado

from app import config
from app.dominio.modelos import EstadoReporte, Prioridad, Reporte
from app.triaje.clasificador import Resultado, clasificar

Clasificador = Callable[[str], Resultado]

TIEMPO_MAX_CLASIFICACION_S = 10
HILOS_CLASIFICACION = 2

log = logging.getLogger(__name__)


class ServicioTriaje:
    def __init__(self, clasificador: Clasificador = clasificar,
                 tiempo_max_s: float = TIEMPO_MAX_CLASIFICACION_S) -> None:
        self._clasificador = clasificador
        self._tiempo_max_s = tiempo_max_s
        self._ejecutor = ThreadPoolExecutor(max_workers=HILOS_CLASIFICACION)

    def evaluar(self, reporte: Reporte) -> Reporte:
        """Asigna prioridad sugerida aplicando la política de seguridad clínica."""
        try:
            futuro = self._ejecutor.submit(self._clasificador, reporte.descripcion)
            resultado = futuro.result(timeout=self._tiempo_max_s)
        except TiempoAgotado:
            log.warning("Triaje del reporte %s sin respuesta en %s s",
                        reporte.codigo, self._tiempo_max_s)
            self._descartar_ejecutor(futuro)
            return self._falla_segura(reporte)
        except Exception:
            log.exception("Falla del clasificador en el reporte %s", reporte.codigo)
            return self._falla_segura(reporte)

        reporte.prioridad = resultado.prioridad
        reporte.confianza = resultado.confianza
        reporte.evidencias = resultado.evidencias
        if resultado.confianza < config.UMBRAL_CONFIANZA and resultado.prioridad in (
            Prioridad.MEDIA, Prioridad.BAJA,
        ):
            # Nunca se asigna prioridad baja o media automática con baja confianza.
            reporte.estado = EstadoReporte.REQUIERE_REVISION
        else:
            reporte.estado = EstadoReporte.CLASIFICADO
        return reporte

    def _descartar_ejecutor(self, futuro) -> None:
        """BUG-03: una clasificación colgada no debe ocupar los hilos de los reportes siguientes."""
        if not futuro.cancel():
            self._ejecutor.shutdown(wait=False, cancel_futures=True)
            self._ejecutor = ThreadPoolExecutor(max_workers=HILOS_CLASIFICACION)

    @staticmethod
    def _falla_segura(reporte: Reporte) -> Reporte:
        """Sin clasificación, el reporte sube a prioridad alta y exige revisión manual (RN-03)."""
        reporte.prioridad = Prioridad.ALTA
        reporte.confianza = 0.0
        reporte.estado = EstadoReporte.SIN_CLASIFICAR
        reporte.evidencias = ["clasificador no disponible: revisar manualmente"]
        return reporte


RANGO_COLA = {
    Prioridad.CRITICA: 0,
    Prioridad.ALTA: 1,
    "revision": 2,
    Prioridad.MEDIA: 3,
    Prioridad.BAJA: 4,
}


def ordenar_cola(reportes: list[Reporte]) -> list[Reporte]:
    """Ordena por gravedad; los reportes en revisión van sobre la prioridad media (HU-02)."""

    def clave(r: Reporte):
        if r.estado == EstadoReporte.REQUIERE_REVISION:
            rango = RANGO_COLA["revision"]
        else:
            rango = RANGO_COLA[r.prioridad]
        return (rango, r.creado_en)

    return sorted(reportes, key=clave)
