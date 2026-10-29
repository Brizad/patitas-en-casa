"""Entidades de la adopción (fase 3, #85): perfil del adoptante (RF-08)."""
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
