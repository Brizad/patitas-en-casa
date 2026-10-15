"""Casos de uso del rescatista (HU-06, RF-05, RF-15, RN-08; prototipo P-07 a P-09).

Pendiente del issue #46: filtro por zona o radio, canal de la alerta y escalamiento.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.dominio.modelos import (
    EstadoReporte,
    EstadoRescate,
    Prioridad,
    Reporte,
    Rescate,
    ResultadoRescate,
    Usuario,
)
from app.reportes.repositorio import RepositorioReportes
from app.rescates.repositorio import (
    ACTIVOS,
    RepositorioRescates,
    RescateTomado,
    RescatistaOcupado,
)

# Media y baja no se ofrecen a rescatistas: las programa el refugio (prototipo).
PRIORIDADES_DE_RESCATE = (Prioridad.CRITICA, Prioridad.ALTA)


class RescateNoOfrecido(LookupError):
    pass


class PasoInvalido(Exception):
    """El paso no corresponde al estado del rescate; el mensaje se muestra tal cual."""


class ServicioRescates:
    def __init__(self, reportes: RepositorioReportes, rescates: RepositorioRescates,
                 reloj: Callable[[], datetime] | None = None) -> None:
        self._reportes = reportes
        self._rescates = rescates
        self._reloj = reloj or (lambda: datetime.now(UTC))

    @staticmethod
    def se_ofrece(reporte: Reporte | None) -> bool:
        return (reporte is not None and reporte.estado == EstadoReporte.CONFIRMADO
                and reporte.prioridad in PRIORIDADES_DE_RESCATE)

    def cambiar_disponibilidad(self, rescatista: Usuario, disponible: bool) -> None:
        self._rescates.poner_disponible(rescatista.correo, disponible)

    def ofertas(self, rescatista: Usuario) -> list[Reporte]:
        """Confirmados críticos o altos sin rescatista, solo para quien está disponible."""
        if not self._rescates.esta_disponible(rescatista.correo):
            return []
        tomados = self._rescates.codigos_tomados()
        libres = [r for r in self._reportes.todos()
                  if self.se_ofrece(r) and r.codigo not in tomados]
        return sorted(libres, key=lambda r: (PRIORIDADES_DE_RESCATE.index(r.prioridad),
                                             r.creado_en))

    def aceptar(self, rescatista: Usuario, codigo: str) -> tuple[Rescate, Reporte]:
        reporte = self._reportes.buscar(codigo)
        if not self.se_ofrece(reporte):
            raise RescateNoOfrecido("No hay un rescate ofrecido con ese código.")
        if not self._rescates.esta_disponible(rescatista.correo):
            raise PasoInvalido("Márcate como disponible para aceptar rescates (RF-15).")
        try:
            rescate = self._rescates.aceptar(codigo, rescatista.correo, self._reloj())
        except RescateTomado as error:
            raise PasoInvalido("Otro rescatista ya tomó este rescate.") from error
        except RescatistaOcupado as error:
            raise PasoInvalido("Ya tienes un rescate activo (RN-08).") from error
        return rescate, reporte

    def _avanzar(self, rescatista: Usuario, codigo: str, desde: EstadoRescate,
                 hasta: EstadoRescate, resultado: ResultadoRescate | None = None) -> bool:
        return self._rescates.avanzar(codigo, rescatista.correo, desde, hasta, self._reloj(),
                                      resultado)

    def llegue(self, rescatista: Usuario, codigo: str) -> None:
        if not self._avanzar(rescatista, codigo, EstadoRescate.EN_CAMINO,
                             EstadoRescate.EN_SITIO):
            raise PasoInvalido("Ese rescate no está en camino contigo.")

    def liberar(self, rescatista: Usuario, codigo: str) -> None:
        """El rescate vuelve a ofrecerse a los rescatistas disponibles."""
        for desde in ACTIVOS:
            if self._avanzar(rescatista, codigo, desde, EstadoRescate.LIBERADO):
                return
        raise PasoInvalido("No tienes ese rescate activo.")

    def registrar_resultado(self, rescatista: Usuario, codigo: str,
                            resultado: ResultadoRescate) -> None:
        if self._avanzar(rescatista, codigo, EstadoRescate.EN_SITIO, EstadoRescate.ATENDIDO,
                         resultado):
            return
        actual = self._rescates.vigente(codigo)
        if (actual and actual.rescatista == rescatista.correo
                and actual.estado == EstadoRescate.EN_CAMINO):
            raise PasoInvalido("Primero marca Llegué al sitio.")
        raise PasoInvalido("No tienes ese rescate activo.")

    def mio(self, rescatista: Usuario) -> tuple[Rescate, Reporte] | None:
        rescate = self._rescates.activo_de(rescatista.correo)
        if rescate is None:
            return None
        return rescate, self._reportes.buscar(rescate.codigo)
