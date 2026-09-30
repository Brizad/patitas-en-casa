"""Política de decisión del Motor de Triaje (RNF-03 y flujo E1 del UC-01)."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as TiempoAgotado
from typing import Callable

from app import config
from app.dominio.modelos import EstadoReporte, Prioridad, Reporte
from app.triaje.clasificador import Resultado, clasificar

Clasificador = Callable[[str], Resultado]

TIEMPO_MAX_CLASIFICACION_S = 10


class ServicioTriaje:
    def __init__(self, clasificador: Clasificador = clasificar,
                 tiempo_max_s: float = TIEMPO_MAX_CLASIFICACION_S) -> None:
        self._clasificador = clasificador
        self._tiempo_max_s = tiempo_max_s
        self._ejecutor = ThreadPoolExecutor(max_workers=2)

    def evaluar(self, reporte: Reporte) -> Reporte:
        """Asigna prioridad sugerida aplicando la política de seguridad clínica."""
        try:
            futuro = self._ejecutor.submit(self._clasificador, reporte.descripcion)
            resultado = futuro.result(timeout=self._tiempo_max_s)
        except (TiempoAgotado, Exception):
            # Falla segura: sin clasificación, el reporte sube a prioridad alta.
            reporte.prioridad = Prioridad.ALTA
            reporte.confianza = 0.0
            reporte.estado = EstadoReporte.SIN_CLASIFICAR
            reporte.evidencias = ["clasificador no disponible: revisar manualmente"]
            return reporte

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
