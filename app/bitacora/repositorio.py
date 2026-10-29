"""Bitácora general de cambios (RF-32, RNF-12, fase 5, #102).

Cada petición que cambia datos y termina bien queda registrada: quién (correo o «anónimo»),
qué (método y ruta, p. ej. «POST /refugio/animales/{animal_id}/egreso»), sobre qué (los
parámetros de la ruta) y cuándo. NUNCA se guarda el cuerpo de la petición: ahí van
contraseñas, descripciones y datos personales (Ley 1581).

RNF-12 (#149): en los cambios importantes (prioridad, descarte, cuentas, solicitudes,
cupos) también el valor anterior y el nuevo. Solo estados y cifras, nunca datos personales:
del perfil del adoptante se guarda qué campos cambiaron, no sus valores.

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
    anterior: dict | None = None  # RNF-12: cómo estaba (None si no aplica)
    nuevo: dict | None = None  # RNF-12: cómo quedó


class RepositorioBitacora(Protocol):
    def registrar(self, evento: Evento) -> None: ...

    def recientes(self, limite: int = 100) -> list[Evento]:
        """Los últimos eventos, el más reciente primero."""
        ...

    def de_actor(self, actor: str, accion: str, limite: int = 50) -> list[Evento]:
        """RF-16: los eventos de una cuenta (p. ej. sus inicios de sesión), recientes primero."""
        ...


class RepositorioBitacoraEnMemoria:
    def __init__(self) -> None:
        self._eventos: list[Evento] = []

    def registrar(self, evento: Evento) -> None:
        self._eventos.append(evento)

    def recientes(self, limite: int = 100) -> list[Evento]:
        return list(reversed(self._eventos[-limite:]))

    def de_actor(self, actor: str, accion: str, limite: int = 50) -> list[Evento]:
        return [e for e in reversed(self._eventos)
                if e.actor == actor and e.accion == accion][:limite]
