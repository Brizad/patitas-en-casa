"""Casos de uso del rescatista (HU-06, RF-05, RF-15, RF-23, RN-08; prototipo P-07 a P-09).

Decisión del autor en #46: zona por comunas de Cúcuta, alerta por correo y escalamiento al
coordinador si nadie acepta a tiempo (crítico 15 min; alto 30 min según el prototipo). Al
escalar, el caso se ofrece en toda la ciudad ("se amplía el radio" del prototipo).
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app import config
from app.avisos.modelos import AvisoNuevo
from app.cupos.servicio import Notificador
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

log = logging.getLogger(__name__)

# Media y baja no se ofrecen a rescatistas: las programa el refugio (prototipo).
PRIORIDADES_DE_RESCATE = (Prioridad.CRITICA, Prioridad.ALTA)
NOMBRE_PRIORIDAD = {Prioridad.CRITICA: "crítico", Prioridad.ALTA: "alto"}


def en_zona(reporte: Reporte, comunas: frozenset[int]) -> bool:
    """Sin zona = toda la ciudad; un reporte sin comuna se ofrece a todos."""
    comuna = reporte.ubicacion.comuna
    return not comunas or comuna is None or comuna in comunas


def _lugar(reporte: Reporte) -> str:
    comuna = reporte.ubicacion.comuna
    return f"en la comuna {comuna}" if comuna else "sin comuna indicada"


class RescateNoOfrecido(LookupError):
    pass


class PasoInvalido(Exception):
    """El paso no corresponde al estado del rescate; el mensaje se muestra tal cual."""


class ServicioRescates:
    def __init__(self, reportes: RepositorioReportes, rescates: RepositorioRescates, *,
                 notificador: Notificador | None = None,
                 reloj: Callable[[], datetime] | None = None) -> None:
        self._reportes = reportes
        self._rescates = rescates
        self._notificador = notificador
        self._reloj = reloj or (lambda: datetime.now(UTC))

    @staticmethod
    def se_ofrece(reporte: Reporte | None) -> bool:
        return (reporte is not None and reporte.estado == EstadoReporte.CONFIRMADO
                and reporte.prioridad in PRIORIDADES_DE_RESCATE)

    def cambiar_disponibilidad(self, rescatista: Usuario, disponible: bool) -> None:
        self._rescates.poner_disponible(rescatista.correo, disponible)

    def cambiar_zona(self, rescatista: Usuario, comunas: frozenset[int]) -> None:
        if not comunas <= set(config.COMUNAS_CUCUTA):
            raise ValueError("Las comunas de Cúcuta van de 1 a 10.")
        self._rescates.poner_zona(rescatista.correo, comunas)

    def zona(self, rescatista: Usuario) -> frozenset[int]:
        return self._rescates.zona(rescatista.correo)

    def esta_disponible(self, rescatista: Usuario) -> bool:
        return self._rescates.esta_disponible(rescatista.correo)

    def ofertas(self, rescatista: Usuario) -> list[Reporte]:
        """Confirmados críticos o altos sin rescatista de su zona (o ya escalados), solo para
        quien está disponible."""
        if not self._rescates.esta_disponible(rescatista.correo):
            return []
        tomados = self._rescates.codigos_tomados()
        escalados = self._rescates.escalados()
        zona = self._rescates.zona(rescatista.correo)
        libres = [r for r in self._reportes.todos()
                  if self.se_ofrece(r) and r.codigo not in tomados
                  and (r.codigo in escalados or en_zona(r, zona))]
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

    def escalados(self) -> set[str]:
        return self._rescates.escalados()

    # --- Alertas por correo (#46) ---------------------------------------------------

    def _avisar(self, destinatario: str, mensaje: str) -> None:
        """Una falla del correo nunca deshace la confirmación ni detiene el escalamiento."""
        if self._notificador is None:
            return
        try:
            self._notificador.enviar(destinatario, mensaje)
        except Exception as error:
            log.error("No se pudo avisar a %s (%s).", destinatario, type(error).__name__)

    def _libres_para_avisar(self, condicion: Callable[[frozenset[int]], bool]) -> list[str]:
        """Disponibles sin rescate activo (RN-08: no podrían aceptar) que cumplen la
        condición sobre su zona."""
        return sorted(correo for correo, zona in self._rescates.disponibles().items()
                      if condicion(zona) and self._rescates.activo_de(correo) is None)

    def avisos_para(self, reporte: Reporte, prioridad: Prioridad) -> list[AvisoNuevo]:
        """RF-05: un aviso para cada uno de los rescatistas libres de la zona si el reporte
        queda crítico o alto con esa prioridad. El correo no lleva la dirección: se entrega al
        aceptar. No envía nada: decidir a quién avisar y enviar son pasos distintos (II-03)."""
        if prioridad not in PRIORIDADES_DE_RESCATE:
            return []
        mensaje = (f"Rescate {NOMBRE_PRIORIDAD[prioridad]} {reporte.codigo} {_lugar(reporte)}. "
                   "Entra a Patitas en Casa para aceptarlo.")
        return [AvisoNuevo(correo, mensaje)
                for correo in self._libres_para_avisar(lambda zona: en_zona(reporte, zona))]

    def alertar_confirmado(self, codigo: str) -> None:
        """Envío directo de los avisos de un reporte ya confirmado (camino anterior a #63)."""
        reporte = self._reportes.buscar(codigo)
        if not self.se_ofrece(reporte):
            return
        for aviso in self.avisos_para(reporte, reporte.prioridad):
            self._avisar(aviso.destinatario, aviso.mensaje)

    def escalar_vencidos(self) -> list[str]:
        """RF-23: sin aceptar a tiempo → aviso al coordinador (una vez) y oferta en toda la
        ciudad, con aviso a los rescatistas de otras zonas. Devuelve los códigos escalados.

        El tiempo cuenta desde la confirmación del veterinario."""
        ahora = self._reloj()
        tomados = self._rescates.codigos_tomados()
        ya_escalados = self._rescates.escalados()
        escalados = []
        for reporte in self._reportes.todos():
            if (not self.se_ofrece(reporte) or reporte.codigo in tomados
                    or reporte.codigo in ya_escalados):
                continue
            decisiones = self._reportes.decisiones(reporte.codigo)
            minutos = config.ESCALAMIENTO_MINUTOS[reporte.prioridad.value]
            if not decisiones or ahora - decisiones[-1].decidido_en < timedelta(minutes=minutos):
                continue
            if not self._rescates.marcar_escalado(reporte.codigo, ahora):
                continue  # otro proceso lo escaló primero
            escalados.append(reporte.codigo)
            self._avisar_escalamiento(reporte, minutos)
        return escalados

    def _avisar_escalamiento(self, reporte: Reporte, minutos: int) -> None:
        nombre = NOMBRE_PRIORIDAD[reporte.prioridad]
        self._avisar("coordinadores",
                     f"Rescate {nombre} {reporte.codigo} sin aceptar hace {minutos} min "
                     f"({_lugar(reporte)}). Se ofreció a todos los rescatistas disponibles.")
        mensaje = (f"Rescate {nombre} {reporte.codigo} {_lugar(reporte)} sigue sin rescatista. "
                   "Entra a Patitas en Casa para aceptarlo.")
        # A los de la zona ya se les avisó al confirmar; ahora se amplía a los demás.
        for correo in self._libres_para_avisar(lambda zona: not en_zona(reporte, zona)):
            self._avisar(correo, mensaje)

    def mio(self, rescatista: Usuario) -> tuple[Rescate, Reporte] | None:
        rescate = self._rescates.activo_de(rescatista.correo)
        if rescate is None:
            return None
        return rescate, self._reportes.buscar(rescate.codigo)
