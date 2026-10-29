"""Análisis de video y fusión con el texto (RF-03, RF-19, RN-07, fase 4, #95).

Lo que SÍ está construido: el puerto `AnalizadorVideo` (lo que el triaje espera de un
analizador) y la regla RN-07 en `fusionar`: si texto y video discrepan, gana la prioridad más
alta. También `aplicar_video`, que actualiza un reporte ya clasificado cuando llega el
resultado del video (el análisis es asíncrono: RNF-02 da hasta 3 minutos y el ciudadano no
espera).

Lo que NO está construido (DT-10 en DEUDA_TECNICA.md): el adaptador real con MediaPipe Pose.
MediaPipe + OpenCV y el modelo de pose pasan de 150 MB instalados y, al procesar 60 s de
video, la memoria no cabe junto a la API en los 512 MB del plan gratis de Render. Además el
reporte todavía no sube el archivo (RF-01 solo valida duración y tamaño).
"""
from __future__ import annotations

from typing import Protocol

from app.dominio.modelos import EstadoReporte, Reporte
from app.triaje.clasificador import ORDEN_GRAVEDAD, Resultado


class VideoNoDisponible(RuntimeError):
    pass


class AnalizadorVideo(Protocol):
    def analizar(self, ruta: str) -> Resultado:
        """Prioridad, confianza y evidencias a partir de la marcha del animal (pose)."""
        ...


class AnalizadorNoDisponible:
    """Adaptador por defecto mientras no haya un worker con MediaPipe (DT-10)."""

    def analizar(self, ruta: str) -> Resultado:
        raise VideoNoDisponible("El análisis de video no está disponible en este despliegue.")


def fusionar(texto: Resultado, video: Resultado | None) -> Resultado:
    """RN-07: gana la prioridad más alta (más grave). Sin video, manda el texto."""
    if video is None:
        return texto
    evidencias = texto.evidencias + [f"video: {e}" for e in video.evidencias]
    if video.prioridad != texto.prioridad:  # RF-19: la discrepancia queda registrada
        evidencias.append(f"discrepancia: texto {texto.prioridad.value}, video "
                          f"{video.prioridad.value}; gana la más alta (RN-07)")
    if ORDEN_GRAVEDAD.index(video.prioridad) < ORDEN_GRAVEDAD.index(texto.prioridad):
        return Resultado(video.prioridad, video.confianza, evidencias)
    return Resultado(texto.prioridad, texto.confianza, evidencias)


def aplicar_video(reporte: Reporte, video: Resultado) -> bool:
    """Si el reporte aún espera al veterinario y el video es más grave, sube su prioridad.
    Devuelve True si cambió. Un reporte ya confirmado o descartado no se toca: lo decidió
    una persona (RN-16)."""
    if reporte.estado in (EstadoReporte.CONFIRMADO, EstadoReporte.DESCARTADO):
        return False
    actual = Resultado(reporte.prioridad, reporte.confianza or 0.0, list(reporte.evidencias))
    fusion = fusionar(actual, video)
    reporte.evidencias = fusion.evidencias
    if fusion.prioridad == reporte.prioridad:
        return False
    reporte.prioridad, reporte.confianza = fusion.prioridad, fusion.confianza
    reporte.estado = EstadoReporte.CLASIFICADO  # subió a una prioridad más grave
    return True
