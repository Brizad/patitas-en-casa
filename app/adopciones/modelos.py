"""Entidades de la adopción (fase 3, #85): perfil (RF-08) y publicación (RF-25)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum


class Vivienda(StrEnum):
    CASA = "casa"
    APARTAMENTO = "apartamento"
    FINCA = "finca"


@dataclass
class PerfilAdoptante:
    """RF-08. Solo lo necesario para decidir y recomendar (RNF-08, Ley 1581: datos mínimos).

    No se piden edad, género, estrato, religión ni etnia: no sirven para decidir si un animal
    estará bien cuidado y son atributos protegidos (RNF-16).
    """

    correo: str
    vivienda: Vivienda
    tiene_patio: bool
    hay_ninos: bool
    otros_animales: bool
    horas_solo_al_dia: int  # horas que el animal pasaría sin nadie en casa
    experiencia: bool  # ya cuidó perros o gatos
    acepta_seguimiento: bool  # RF-10: visitas o llamadas a los 30, 90 y 180 días
    actualizado_en: datetime = field(default_factory=lambda: datetime.now(UTC))

    def habilitado(self) -> bool:
        """RN-10: solo solicita quien acepta el seguimiento posterior."""
        return self.acepta_seguimiento


class Tamano(StrEnum):
    PEQUENO = "pequeno"
    MEDIANO = "mediano"
    GRANDE = "grande"


class Energia(StrEnum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EstadoPublicacion(StrEnum):
    DISPONIBLE = "disponible"
    ADOPTADO = "adoptado"


@dataclass
class Publicacion:
    """RF-25: un animal del refugio ofrecido en adopción, con lo que necesita su nuevo hogar.

    nombre y especie se leen de la ficha del animal (no se escriben dos veces).
    """

    animal_id: int
    descripcion: str
    tamano: Tamano
    energia: Energia
    edad_meses: int
    apto_ninos: bool
    apto_otros_animales: bool
    necesita_patio: bool
    nombre: str = ""
    especie: str = ""
    estado: EstadoPublicacion = EstadoPublicacion.DISPONIBLE
    publicado_en: datetime = field(default_factory=lambda: datetime.now(UTC))


class EstadoSolicitud(StrEnum):
    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


@dataclass
class Solicitud:
    """RF-27: un adoptante pide adoptar un animal publicado; el refugio decide."""

    id: int | None
    animal_id: int
    adoptante: str  # correo de la cuenta
    mensaje: str
    estado: EstadoSolicitud
    creada_en: datetime
    decidida_por: str | None = None  # correo del coordinador
    decidida_en: datetime | None = None
    razon: str | None = None  # obligatoria al rechazar


DIAS_SEGUIMIENTO = (30, 90, 180)  # RF-10


@dataclass
class Seguimiento:
    """RF-10: visita o llamada después de la adopción."""

    id: int | None
    solicitud_id: int
    dia: int  # 30, 90 o 180
    programado_para: datetime
    realizado_en: datetime | None = None
    nota: str | None = None
    registrado_por: str | None = None
