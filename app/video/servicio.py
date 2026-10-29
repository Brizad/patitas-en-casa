"""Casos de uso del video del reporte (#125, RF-03, RF-19, RN-07, RNF-02).

1. El ciudadano adjunta el video justo después de crear el reporte (solo él tiene la clave de
   idempotencia con la que lo creó).
2. El trabajador local reclama el trabajo, descarga el video y devuelve el resultado.
3. Aquí se aplica RN-07 (gana la prioridad más alta) sin tocar lo que ya decidió el
   veterinario, se registra la discrepancia (RF-19) y se borra el video.

Falla segura: si el video se pierde, no es concluyente o nadie lo analiza a tiempo, el reporte
sigue con la prioridad del texto.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app import config
from app.dominio.modelos import DECIDIDOS
from app.reportes.repositorio import RepositorioReportes
from app.triaje.clasificador import Resultado
from app.triaje.video import aplicar_video
from app.video.modelos import EstadoVideo, ResultadoVideo, TrabajoVideo
from app.video.repositorio import RepositorioVideos


class VideoRechazado(Exception):
    def __init__(self, estado_http: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http


class AlmacenVideos(Protocol):
    def existe(self, ruta: str) -> bool: ...
    def borrar(self, ruta: str) -> None: ...


class ServicioVideo:
    def __init__(self, videos: RepositorioVideos, reportes: RepositorioReportes,
                 almacen: AlmacenVideos, reloj: Callable[[], datetime] | None = None) -> None:
        self._videos, self._reportes, self._almacen = videos, reportes, almacen
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def autorizar_subida(self, codigo: str, clave: str | None) -> None:
        """Antes de leer el archivo: solo quien creó el reporte, a tiempo y una sola vez."""
        reporte = self._reportes.buscar_por_clave(clave) if clave else None
        if reporte is None or reporte.codigo != codigo:
            raise VideoRechazado(403, "Solo se puede adjuntar el video desde el teléfono que "
                                      "envió el reporte.")
        ventana = timedelta(minutes=config.VIDEO_VENTANA_SUBIDA_MINUTOS)
        if self._reloj() - reporte.creado_en > ventana:
            raise VideoRechazado(403, "Ya pasó el tiempo para adjuntar el video a este "
                                      "reporte.")
        if self._videos.de_reporte(codigo) is not None:
            raise VideoRechazado(409, "Este reporte ya tiene un video.")

    def registrar(self, codigo: str, ruta: str, tamano: int) -> TrabajoVideo:
        trabajo = self._videos.crear(codigo, ruta, tamano, self._reloj())
        if trabajo is None:  # otro envío del mismo reporte ganó la carrera
            self._almacen.borrar(ruta)
            raise VideoRechazado(409, "Este reporte ya tiene un video.")
        return trabajo

    def de_reporte(self, codigo: str) -> TrabajoVideo | None:
        return self._videos.de_reporte(codigo)

    def reclamar(self) -> TrabajoVideo | None:
        ahora = self._reloj()
        vence = ahora - timedelta(seconds=config.VENCIMIENTO_RECLAMO_VIDEO_S)
        return self._videos.reclamar(ahora, vence)

    def _enviado(self, id_: int) -> TrabajoVideo:
        trabajo = self._videos.buscar(id_)
        if trabajo is None:
            raise VideoRechazado(404, "Trabajo de video no encontrado.")
        if trabajo.estado != EstadoVideo.ENVIADO:
            raise VideoRechazado(409, f"El trabajo está «{trabajo.estado.value}».")
        return trabajo

    def _cerrar(self, trabajo: TrabajoVideo, estado: EstadoVideo, motivo: str | None) -> None:
        trabajo.estado, trabajo.motivo, trabajo.terminado_en = estado, motivo, self._reloj()
        self._videos.guardar(trabajo)
        self._almacen.borrar(trabajo.ruta)  # RNF-08: el video nunca se guarda para siempre

    def ruta_para_descargar(self, id_: int) -> str:
        trabajo = self._enviado(id_)
        if not self._almacen.existe(trabajo.ruta):
            self._cerrar(trabajo, EstadoVideo.FALLIDO, "el video ya no está en el servidor "
                         "(se reinició); manda el texto")
            raise VideoRechazado(410, "El video ya no está disponible.")
        return trabajo.ruta

    def terminar(self, id_: int, resultado: ResultadoVideo) -> TrabajoVideo:
        trabajo = self._enviado(id_)
        trabajo.evidencias, trabajo.medidas = list(resultado.evidencias), dict(resultado.medidas)
        trabajo.version_modelo, trabajo.tira = resultado.version_modelo, resultado.tira
        if resultado.prioridad is None:
            self._cerrar(trabajo, EstadoVideo.NO_CONCLUYENTE,
                         resultado.motivo or "el video no muestra bien al animal")
            return trabajo
        trabajo.prioridad, trabajo.confianza = resultado.prioridad, resultado.confianza
        reporte = self._reportes.buscar(trabajo.codigo)
        if reporte is not None:
            trabajo.discrepancia = reporte.prioridad not in (None, resultado.prioridad)
            if reporte.estado not in DECIDIDOS:  # RN-16: lo decidido por una persona no cambia
                aplicar_video(reporte, Resultado(resultado.prioridad, resultado.confianza,
                                                 list(resultado.evidencias)))
                self._reportes.actualizar_triaje(reporte)
        self._cerrar(trabajo, EstadoVideo.TERMINADO, None)
        return trabajo

    def fallar(self, id_: int, motivo: str) -> TrabajoVideo:
        """El trabajador no pudo analizarlo: se reintenta; al agotar los intentos, fallido."""
        trabajo = self._enviado(id_)
        trabajo.intentos += 1
        if trabajo.intentos >= config.MAX_INTENTOS_VIDEO:
            self._cerrar(trabajo, EstadoVideo.FALLIDO, motivo[:300])
        else:
            trabajo.estado, trabajo.reclamado_en, trabajo.motivo = (
                EstadoVideo.PENDIENTE, None, motivo[:300])
            self._videos.guardar(trabajo)
        return trabajo

    def revisar(self) -> int:
        """Periódico: lo que nadie analizó en VIDEO_MAX_ESPERA_HORAS se da por fallido (el
        trabajador local estuvo apagado) y su video se borra."""
        limite = self._reloj() - timedelta(hours=config.VIDEO_MAX_ESPERA_HORAS)
        vencidos = self._videos.esperando_desde_antes(limite)
        for trabajo in vencidos:
            self._cerrar(trabajo, EstadoVideo.FALLIDO, "nadie lo analizó a tiempo; manda el "
                         "texto")
        return len(vencidos)
