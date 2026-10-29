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
    DESCARTADO = "descartado"  # D-02 (#75): falso o duplicado; sale de la cola


# Estados en los que el veterinario ya decidió: el reporte no vuelve a la cola.
DECIDIDOS = frozenset({EstadoReporte.CONFIRMADO, EstadoReporte.DESCARTADO})


class MotivoDescarte(StrEnum):
    FALSO = "falso"
    DUPLICADO = "duplicado"


@dataclass
class Ubicacion:
    latitud: float | None = None
    longitud: float | None = None
    direccion: str | None = None
    comuna: int | None = None  # HU-06: comuna de Cúcuta (1 a 10); opcional

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
    version_modelo: str | None = None  # RF-20: quién sugirió; None en falla segura (RN-03)


@dataclass
class Animal:
    """Animal ingresado al refugio con su ficha clínica mínima (RF-06)."""

    nombre: str
    especie: Especie
    estado_salud: str
    vacunado: bool = False
    esterilizado: bool = False
    id: int | None = None  # #75: lo asigna el repositorio al ingresar
    ingresado_en: datetime | None = None


class TipoNota(StrEnum):
    """Tipos de nota del historial clínico (RF-24)."""

    OBSERVACION = "observacion"
    TRATAMIENTO = "tratamiento"
    VACUNA = "vacuna"
    PROCEDIMIENTO = "procedimiento"


@dataclass
class NotaClinica:
    """Una entrada del historial clínico (RF-24): solo se agrega, nunca se edita."""

    animal_id: int
    autor: str  # correo del veterinario
    tipo: TipoNota
    texto: str
    registrada_en: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DecisionTriaje:
    """Confirmación o ajuste de la prioridad por un veterinario (HU-02, RN-06, RN-16).

    Queda en la bitácora: quién decidió, qué sugería el triaje y por qué se cambió.
    """

    codigo: str
    veterinario: str  # correo de la cuenta
    prioridad_sugerida: Prioridad
    prioridad_final: Prioridad
    justificacion: str | None = None
    decidido_en: datetime = field(default_factory=lambda: datetime.now(UTC))
    version_modelo: str | None = None  # RF-20, D-04: versión que hizo la sugerencia

    @property
    def ajustada(self) -> bool:
        return self.prioridad_final != self.prioridad_sugerida


@dataclass
class Descarte:
    """D-02: el veterinario descarta un reporte falso o duplicado, con justificación."""

    codigo: str
    veterinario: str  # correo de la cuenta
    motivo: MotivoDescarte
    justificacion: str
    duplicado_de: str | None = None
    descartado_en: datetime = field(default_factory=lambda: datetime.now(UTC))


class Rol(StrEnum):
    """Roles del personal con cuenta (DT-02). El ciudadano reporta sin cuenta (RF-01)."""

    VETERINARIO = "veterinario"
    COORDINADOR = "coordinador"
    RESCATISTA = "rescatista"  # HU-06: voluntario que atiende rescates en campo
    ADMINISTRADOR = "administrador"  # #67: refugios y cuentas (RF-14, RF-16)


class EstadoRescate(StrEnum):
    """Ciclo del rescate (HU-06, prototipo P-07 a P-09)."""

    EN_CAMINO = "en_camino"
    EN_SITIO = "en_sitio"
    ATENDIDO = "atendido"
    LIBERADO = "liberado"  # el rescatista lo soltó: vuelve a ofrecerse


class ResultadoRescate(StrEnum):
    TRASLADADO = "trasladado"  # trasladado a refugio
    ATENDIDO_EN_SITIO = "atendido_en_sitio"
    NO_ENCONTRADO = "no_encontrado"
    FALLECIDO = "fallecido"


@dataclass
class Rescate:
    """Un rescatista atendiendo un reporte confirmado (RN-08: uno por rescate y por persona)."""

    codigo: str
    rescatista: str  # correo de la cuenta
    estado: EstadoRescate
    aceptado_en: datetime
    actualizado_en: datetime
    resultado: ResultadoRescate | None = None


@dataclass
class Usuario:
    correo: str
    nombre: str
    rol: Rol
    hash_contrasena: str = field(repr=False)  # Argon2id; nunca la contraseña
    activo: bool = True
    refugio_id: int | None = None  # #67 (RF-14): refugio donde trabaja; None = ninguno


@dataclass
class Refugio:
    nombre: str
    capacidad: int
    ocupados: int = 0
    id: int | None = None  # #67: None mientras no se ha guardado

    def __post_init__(self) -> None:
        # BUG-04: invariante del refugio (DAD 7.2).
        if self.capacidad <= 0:
            raise ValueError("La capacidad del refugio debe ser mayor que cero.")
        if not 0 <= self.ocupados <= self.capacidad:
            raise ValueError("Los cupos ocupados deben estar entre 0 y la capacidad.")

    def tiene_cupo(self) -> bool:
        return self.ocupados < self.capacidad

    def porcentaje_ocupacion(self) -> float:
        return self.ocupados / self.capacidad

    def texto_ocupacion(self) -> str:
        return f"{self.ocupados}/{self.capacidad}"
