"""Entidades del dominio (FPI-09): lenguaje ubicuo de Patitas en Casa."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Especie(StrEnum):
    PERRO = "perro"
    GATO = "gato"


class Prioridad(StrEnum):
    """Escala de triaje (RF-02). Tiempos objetivo preliminares, a validar con veterinarios."""

    CRITICA = "critica"  # atención en 1 hora o menos
    ALTA = "alta"  # 6 horas o menos
    MEDIA = "media"  # 24 horas o menos
    BAJA = "baja"  # 72 horas o menos


class EstadoReporte(StrEnum):
    RECIBIDO = "recibido"
    CLASIFICADO = "clasificado"
    REQUIERE_REVISION = "requiere_revision"
    SIN_CLASIFICAR = "sin_clasificar"
    CONFIRMADO = "confirmado"


@dataclass
class Ubicacion:
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = None

    def es_valida(self) -> bool:
        tiene_gps = self.latitud is not None and self.longitud is not None
        return tiene_gps or bool(self.direccion and self.direccion.strip())


@dataclass
class Reporte:
    """Reporte de emergencia hecho por un ciudadano, sin cuenta (RF-01)."""

    codigo: str
    descripcion: str
    ubicacion: Ubicacion
    video_segundos: int | None = None
    estado: EstadoReporte = EstadoReporte.RECIBIDO
    prioridad: Prioridad | None = None
    confianza: float | None = None
    evidencias: list[str] = field(default_factory=list)
    creado_en: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Animal:
    """Animal ingresado al refugio con su ficha clínica mínima (RF-06)."""

    nombre: str
    especie: Especie
    estado_salud: str
    vacunado: bool = False
    esterilizado: bool = False


@dataclass
class Refugio:
    nombre: str
    capacidad: int
    ocupados: int = 0

    def tiene_cupo(self) -> bool:
        return self.ocupados < self.capacidad

    def porcentaje_ocupacion(self) -> float:
        return self.ocupados / self.capacidad

    def texto_ocupacion(self) -> str:
        return f"{self.ocupados}/{self.capacidad}"
