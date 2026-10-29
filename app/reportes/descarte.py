"""Caso de uso: el veterinario descarta un reporte falso o duplicado (D-02, #75).

Descartar es la otra salida de la cola, además de confirmar: por eso usa las mismas reglas
(solo el veterinario, una sola vez, justificación de RN-16 con letras de D-07) y la misma
idea del UPDATE condicional en el repositorio.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.dominio.modelos import Descarte, MotivoDescarte, Rol, Usuario
from app.reportes.confirmacion import (
    ReporteNoEncontrado,
    ReporteYaConfirmado,
    validar_justificacion,
)
from app.reportes.repositorio import RepositorioReportes


class DescarteInvalido(ValueError):
    pass


class ServicioDescarte:
    def __init__(self, repositorio: RepositorioReportes,
                 reloj: Callable[[], datetime] | None = None) -> None:
        self._repositorio = repositorio
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def descartar(self, codigo: str, veterinario: Usuario, motivo: MotivoDescarte,
                  justificacion: str | None, duplicado_de: str | None = None) -> Descarte:
        if veterinario.rol != Rol.VETERINARIO:
            raise PermissionError("Solo el veterinario descarta reportes (D-02).")
        if self._repositorio.buscar(codigo) is None:
            raise ReporteNoEncontrado(f"No existe el reporte {codigo}.")
        justificacion = (justificacion or "").strip()
        validar_justificacion(justificacion, DescarteInvalido)
        if duplicado_de is not None:
            # El original debe existir y ser otro: así la bitácora apunta a algo real.
            if duplicado_de == codigo or self._repositorio.buscar(duplicado_de) is None:
                raise DescarteInvalido("El reporte original del duplicado no existe.")
        descarte = Descarte(codigo=codigo, veterinario=veterinario.correo, motivo=motivo,
                            justificacion=justificacion, duplicado_de=duplicado_de,
                            descartado_en=self._reloj())
        if not self._repositorio.descartar(descarte):
            raise ReporteYaConfirmado(f"El reporte {codigo} ya fue confirmado o descartado.")
        return descarte
