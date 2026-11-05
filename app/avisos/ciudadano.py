"""Avisos al ciudadano que dejó un correo (RF-18, #282): antes vivían dentro de crear_app."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.avisos.modelos import AvisoNuevo
from app.avisos.repositorio import RepositorioAvisos
from app.dominio.modelos import Reporte
from app.reportes.repositorio import RepositorioReportes
from app.seguridad.cifrado import PREFIJO_AVISO, Cifrador

logger = logging.getLogger("app.api.main")  # el mismo de antes: los logs no cambian


class AvisosAlCiudadano:
    def __init__(self, repositorio: RepositorioReportes, avisos: RepositorioAvisos,
                 cifrador: Cifrador | None) -> None:
        self._repositorio = repositorio
        self._avisos = avisos
        self._cifrador = cifrador

    def para(self, reporte: Reporte, texto: str) -> list[AvisoNuevo]:
        """Solo si el ciudadano dejó un correo y autorizó el contacto (el contacto solo se
        guarda con la autorización). RN-14: el texto lleva el código y nada más; el
        destinatario va cifrado también en la tabla de avisos."""
        if not reporte.contacto_cifrado or self._cifrador is None:
            return []
        if "@" not in self._cifrador.descifrar(reporte.contacto_cifrado):
            return []  # un teléfono se guarda, pero no hay correo al cual avisar
        return [AvisoNuevo(PREFIJO_AVISO + reporte.contacto_cifrado,
                           f"Patitas en Casa: {texto}")]

    def avisar(self, codigo: str, texto: str) -> None:
        """Guarda el aviso en el outbox; el envío es del procesador. Una falla aquí no deshace
        el rescate ni el ingreso, que ya ocurrieron: se registra en el log."""
        try:
            reporte = self._repositorio.buscar(codigo)
            if reporte is not None:
                self._avisos.agregar(codigo, self.para(reporte, texto), datetime.now(UTC))
        except Exception:
            logger.exception("No se pudo guardar el aviso al ciudadano del reporte %s.", codigo)
