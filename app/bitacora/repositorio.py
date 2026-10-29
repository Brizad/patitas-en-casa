"""Bitácora general de cambios (RF-32, RNF-12, fase 5, #102).

Cada petición que cambia datos y termina bien queda registrada: quién (correo o «anónimo»),
qué (método y ruta, p. ej. «POST /refugio/animales/{animal_id}/egreso»), sobre qué (los
parámetros de la ruta) y cuándo. NUNCA se guarda el cuerpo de la petición: ahí van
contraseñas, descripciones y datos personales (Ley 1581).

Inmutable: el repositorio solo tiene «registrar» y «recientes»; no hay editar ni borrar. En
PostgreSQL, además, un disparador rechaza UPDATE y DELETE (migración 0020), así que ni
siquiera un error en el código puede alterar la historia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class Evento:
    actor: str  # correo de la cuenta, o «anónimo» (reporte ciudadano, registro)
    accion: str  # método y plantilla de la ruta
    objeto: dict[str, str]  # parámetros de la ruta (códigos, ids); nunca el cuerpo
    estado_http: int
    momento: datetime = field(default_factory=lambda: datetime.now(UTC))


class RepositorioBitacora(Protocol):
    def registrar(self, evento: Evento) -> None: ...

    def recientes(self, limite: int = 100) -> list[Evento]:
        """Los últimos eventos, el más reciente primero."""
        ...


class RepositorioBitacoraEnMemoria:
    def __init__(self) -> None:
        self._eventos: list[Evento] = []

    def registrar(self, evento: Evento) -> None:
        self._eventos.append(evento)

    def recientes(self, limite: int = 100) -> list[Evento]:
        return list(reversed(self._eventos[-limite:]))
