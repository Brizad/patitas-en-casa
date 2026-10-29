"""Caso de uso: el veterinario confirma o ajusta la prioridad sugerida (HU-02, RF-04).

RN-06: solo el veterinario confirma. RN-16: cambiar la prioridad exige justificación y queda
en la bitácora. La IA sugiere; la decisión es del veterinario.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from app import config
from app.avisos.modelos import AvisoNuevo
from app.dominio.modelos import DecisionTriaje, EstadoReporte, Prioridad, Reporte, Rol, Usuario
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


def validar_justificacion(texto: str | None, error: type[Exception]) -> None:
    """RN-16 y D-07: 10 caracteres o más, y letras de verdad. Se cuentan letras (no palabras)
    para aceptar motivos cortos y reales como «Sangra mucho»."""
    texto = texto or ""
    if len(texto) < config.MIN_CARACTERES_JUSTIFICACION:
        raise error(f"Para cambiar la prioridad escribe por qué (mínimo "
                    f"{config.MIN_CARACTERES_JUSTIFICACION} caracteres, RN-16).")
    if sum(letra.isalpha() for letra in texto) < config.MIN_LETRAS_JUSTIFICACION:
        raise error(f"La justificación debe explicar el motivo con palabras (mínimo "
                    f"{config.MIN_LETRAS_JUSTIFICACION} letras, D-07).")


# Decide a quién avisar según el reporte y la prioridad final (ServicioRescates.avisos_para).
PlanificadorAvisos = Callable[[Reporte, Prioridad], list[AvisoNuevo]]


@dataclass(frozen=True)
class ResultadoConfirmacion:
    decision: DecisionTriaje
    avisos: int  # avisos guardados como pendientes; enviarlos es trabajo del procesador


class ServicioConfirmacion:
    def __init__(self, repositorio: RepositorioReportes,
                 reloj: Callable[[], datetime] | None = None, *,
                 planificar_avisos: PlanificadorAvisos | None = None) -> None:
        self._repositorio = repositorio
        self._reloj = reloj or (lambda: datetime.now(UTC))
        self._planificar = planificar_avisos or (lambda reporte, prioridad: [])

    def confirmar(self, codigo: str, veterinario: Usuario, prioridad: Prioridad | None = None,
                  justificacion: str | None = None) -> DecisionTriaje:
        return self.confirmar_y_programar(codigo, veterinario, prioridad, justificacion).decision

    def confirmar_y_programar(self, codigo: str, veterinario: Usuario,
                              prioridad: Prioridad | None = None,
                              justificacion: str | None = None) -> ResultadoConfirmacion:
        """Aplica RN-06 y RN-16 y, si se cumplen, guarda la decisión y los avisos pendientes
        juntos (#63). No envía nada: el resultado de negocio no depende del correo."""
        if veterinario.rol != Rol.VETERINARIO:
            raise PermissionError("Solo el veterinario confirma la prioridad (RN-06).")
        reporte = self._repositorio.buscar(codigo)
        if reporte is None:
            raise ReporteNoEncontrado(f"No existe el reporte {codigo}.")
        sugerida = prioridad_sugerida(reporte.estado, reporte.prioridad)
        final = prioridad or sugerida
        justificacion = (justificacion or "").strip() or None
        if final != sugerida:
            validar_justificacion(justificacion, AjusteSinJustificacion)
        decision = DecisionTriaje(codigo=codigo, veterinario=veterinario.correo,
                                  prioridad_sugerida=sugerida, prioridad_final=final,
                                  justificacion=justificacion, decidido_en=self._reloj(),
                                  version_modelo=reporte.version_modelo)
        avisos = self._planificar(reporte, final)
        if not self._repositorio.confirmar(decision, avisos):
            raise ReporteYaConfirmado(f"El reporte {codigo} ya fue confirmado.")
        return ResultadoConfirmacion(decision, len(avisos))
