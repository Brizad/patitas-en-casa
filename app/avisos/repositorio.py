"""Puerto RepositorioAvisos y su versión en memoria (#63, outbox)."""
from __future__ import annotations

import threading
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Protocol

from app.avisos.modelos import Aviso, AvisoNuevo, EstadoAviso


class RepositorioAvisos(Protocol):
    def agregar(self, codigo: str, avisos: Sequence[AvisoNuevo], ahora: datetime) -> int:
        """Guarda los avisos pendientes de un reporte; ignora los repetidos. Devuelve cuántos
        quedaron guardados."""
        ...

    def reclamar(self, ahora: datetime, limite: int, vencimiento: timedelta) -> list[Aviso]:
        """Marca como «enviando» hasta «limite» avisos listos (pendientes cuyo próximo intento
        llegó, o reclamos vencidos de un procesador que se detuvo) y suma un intento. Dos
        procesadores a la vez nunca reclaman el mismo aviso."""
        ...

    def marcar_enviado(self, aviso_id: int, ahora: datetime) -> None: ...

    def marcar_fallo(self, aviso_id: int, error: str, proximo: datetime | None) -> None:
        """Con «proximo» vuelve a pendiente para reintentar; sin él queda fallido."""
        ...

    def de_reporte(self, codigo: str) -> list[Aviso]: ...


def resumen(avisos: Sequence[Aviso]) -> dict[str, int]:
    """Cantidad de avisos por estado, con todos los estados presentes."""
    cuenta = Counter(a.estado for a in avisos)
    return {estado.value: cuenta.get(estado, 0) for estado in EstadoAviso}


class RepositorioAvisosEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[int, Aviso] = {}
        self._candado = threading.RLock()

    def agregar(self, codigo: str, avisos: Sequence[AvisoNuevo], ahora: datetime) -> int:
        with self._candado:
            existentes = {a.destinatario for a in self._datos.values()
                          if a.reporte_codigo == codigo}
            nuevos = 0
            for aviso in avisos:
                if aviso.destinatario in existentes:
                    continue
                existentes.add(aviso.destinatario)
                nuevo_id = len(self._datos) + 1
                self._datos[nuevo_id] = Aviso(nuevo_id, codigo, aviso.destinatario, aviso.mensaje,
                                              EstadoAviso.PENDIENTE, 0, ahora, ahora)
                nuevos += 1
            return nuevos

    def reclamar(self, ahora: datetime, limite: int, vencimiento: timedelta) -> list[Aviso]:
        with self._candado:
            listos = [a for a in sorted(self._datos.values(), key=lambda a: a.id)
                      if (a.estado == EstadoAviso.PENDIENTE and a.proximo_intento_en <= ahora)
                      or (a.estado == EstadoAviso.ENVIANDO
                          and a.reclamado_en < ahora - vencimiento)][:limite]
            for a in listos:
                a.estado, a.intentos, a.reclamado_en = EstadoAviso.ENVIANDO, a.intentos + 1, ahora
            return [replace(a) for a in listos]

    def marcar_enviado(self, aviso_id: int, ahora: datetime) -> None:
        with self._candado:
            aviso = self._datos[aviso_id]
            aviso.estado, aviso.enviado_en, aviso.ultimo_error = EstadoAviso.ENVIADO, ahora, None

    def marcar_fallo(self, aviso_id: int, error: str, proximo: datetime | None) -> None:
        with self._candado:
            aviso = self._datos[aviso_id]
            aviso.ultimo_error = error
            if proximo is None:
                aviso.estado = EstadoAviso.FALLIDO
            else:
                aviso.estado, aviso.proximo_intento_en = EstadoAviso.PENDIENTE, proximo

    def de_reporte(self, codigo: str) -> list[Aviso]:
        with self._candado:
            return [replace(a) for a in sorted(self._datos.values(), key=lambda a: a.id)
                    if a.reporte_codigo == codigo]
