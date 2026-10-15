"""Caso de uso: el veterinario confirma o ajusta la prioridad sugerida (HU-02, RF-04).

RN-06: solo el veterinario confirma. RN-16: cambiar la prioridad exige justificación y queda
en la bitácora. La IA sugiere; la decisión es del veterinario.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app import config
from app.dominio.modelos import DecisionTriaje, EstadoReporte, Prioridad, Rol, Usuario
from app.reportes.repositorio import RepositorioReportes


class ReporteNoEncontrado(LookupError):
    pass


class ReporteYaConfirmado(Exception):
    pass


class AjusteSinJustificacion(ValueError):
    pass


def prioridad_sugerida(estado: EstadoReporte, prioridad: Prioridad | None) -> Prioridad:
    """Sin clasificación (RN-03) la sugerida es alta, como en la falla segura."""
    if estado == EstadoReporte.SIN_CLASIFICAR or prioridad is None:
        return Prioridad.ALTA
    return prioridad


class ServicioConfirmacion:
    def __init__(self, repositorio: RepositorioReportes,
                 reloj: Callable[[], datetime] | None = None) -> None:
        self._repositorio = repositorio
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def confirmar(self, codigo: str, veterinario: Usuario, prioridad: Prioridad | None = None,
                  justificacion: str | None = None) -> DecisionTriaje:
        if veterinario.rol != Rol.VETERINARIO:
            raise PermissionError("Solo el veterinario confirma la prioridad (RN-06).")
        reporte = self._repositorio.buscar(codigo)
        if reporte is None:
            raise ReporteNoEncontrado(f"No existe el reporte {codigo}.")
        sugerida = prioridad_sugerida(reporte.estado, reporte.prioridad)
        final = prioridad or sugerida
        justificacion = (justificacion or "").strip() or None
        if final != sugerida and len(justificacion or "") < config.MIN_CARACTERES_JUSTIFICACION:
            raise AjusteSinJustificacion(
                f"Para cambiar la prioridad escribe por qué (mínimo "
                f"{config.MIN_CARACTERES_JUSTIFICACION} caracteres, RN-16).")
        decision = DecisionTriaje(codigo=codigo, veterinario=veterinario.correo,
                                  prioridad_sugerida=sugerida, prioridad_final=final,
                                  justificacion=justificacion, decidido_en=self._reloj())
        if not self._repositorio.confirmar(decision):
            raise ReporteYaConfirmado(f"El reporte {codigo} ya fue confirmado.")
        return decision
