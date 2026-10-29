"""Trabajos de análisis de video (#125, RF-03, RF-19, RNF-02).

El análisis no corre en Render (no cabe en 512 MB): lo hace un trabajador local que pide los
trabajos a la API. Cada video subido es un trabajo que pasa por estos estados:

    pendiente ──(el trabajador lo reclama)──> enviado ──> terminado
        ^                                        │   └──> no_concluyente (no se ve un perro o
        └──(falla o el reclamo vence: reintento)─┘                         gato, o la calidad
                                                                           no alcanza)
    fallido: se agotaron los intentos, el video se perdió o nadie lo analizó a tiempo.

En los tres finales el video se borra; solo quedan las medidas y las evidencias (RNF-08).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from app.dominio.modelos import Prioridad


class EstadoVideo(StrEnum):
    PENDIENTE = "pendiente"
    ENVIADO = "enviado"
    TERMINADO = "terminado"
    NO_CONCLUYENTE = "no_concluyente"
    FALLIDO = "fallido"


FINALES = frozenset({EstadoVideo.TERMINADO, EstadoVideo.NO_CONCLUYENTE, EstadoVideo.FALLIDO})


@dataclass(frozen=True)
class ResultadoVideo:
    """Lo que devuelve el trabajador. Sin prioridad = video no concluyente."""
    prioridad: Prioridad | None
    confianza: float
    evidencias: list[str]
    medidas: dict = field(default_factory=dict)
    version_modelo: str | None = None
    motivo: str | None = None  # por qué no fue concluyente
    tira: bytes | None = None  # PNG pequeño con 3 cuadros y los puntos dibujados


@dataclass
class TrabajoVideo:
    id: int
    codigo: str
    ruta: str  # archivo temporal en el servidor; se borra al terminar
    bytes: int
    creado_en: datetime
    estado: EstadoVideo = EstadoVideo.PENDIENTE
    intentos: int = 0
    reclamado_en: datetime | None = None
    terminado_en: datetime | None = None
    prioridad: Prioridad | None = None
    confianza: float | None = None
    evidencias: list[str] = field(default_factory=list)
    medidas: dict = field(default_factory=dict)
    version_modelo: str | None = None
    motivo: str | None = None
    discrepancia: bool = False  # RF-19: el video sugirió otra prioridad que el texto
    tira: bytes | None = None
