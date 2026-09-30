"""Caso de uso: registrar un reporte de emergencia sin cuenta (RF-01, HU-01)."""
from __future__ import annotations

import secrets
import string

from app import config
from app.dominio.modelos import Reporte, Ubicacion
from app.reportes.repositorio import RepositorioReportes
from app.triaje.servicio import ServicioTriaje

ALFABETO = string.ascii_uppercase + string.digits
LONGITUD_CODIGO = 8
MIN_CARACTERES_DESCRIPCION = 20


class ReporteInvalido(ValueError):
    pass


def generar_codigo() -> str:
    return "".join(secrets.choice(ALFABETO) for _ in range(LONGITUD_CODIGO))


class ServicioReportes:
    def __init__(self, repositorio: RepositorioReportes, triaje: ServicioTriaje) -> None:
        self._repositorio = repositorio
        self._triaje = triaje

    def registrar(self, descripcion: str, ubicacion: Ubicacion,
                  video_segundos: int | None = None, video_mb: float | None = None) -> Reporte:
        self._validar(descripcion, ubicacion, video_segundos, video_mb)
        codigo = generar_codigo()
        while self._repositorio.buscar(codigo) is not None:
            codigo = generar_codigo()
        reporte = Reporte(codigo=codigo, descripcion=descripcion.strip(),
                          ubicacion=ubicacion, video_segundos=video_segundos)
        self._triaje.evaluar(reporte)
        self._repositorio.guardar(reporte)
        return reporte

    @staticmethod
    def _validar(descripcion, ubicacion, video_segundos, video_mb) -> None:
        if len(descripcion.strip()) < MIN_CARACTERES_DESCRIPCION:
            raise ReporteInvalido("La descripción debe tener al menos 20 caracteres.")
        if not ubicacion.es_valida():
            raise ReporteInvalido("Comparte tu ubicación o escribe una dirección.")
        if video_segundos is not None and video_segundos > config.VIDEO_MAX_SEGUNDOS:
            raise ReporteInvalido("El video debe durar máximo 60 segundos.")
        if video_mb is not None and video_mb > config.VIDEO_MAX_MB:
            raise ReporteInvalido("El video debe pesar máximo 50 MB.")
