"""Avisos a rescatistas guardados antes de enviarse (patrón outbox, #63, D-03 de II-01).

Confirmar un reporte (resultado de negocio) y enviar el correo (efecto externo) son dos cosas
distintas: el aviso se guarda en la misma transacción que la confirmación y un procesador lo
envía después, con reintentos. Así un fallo del correo no se pierde ni se oculta.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class EstadoAviso(StrEnum):
    PENDIENTE = "pendiente"  # guardado, esperando envío o reintento
    ENVIANDO = "enviando"  # un procesador lo reclamó; si se detiene, el reclamo vence
    ENVIADO = "enviado"  # el servidor de correo lo aceptó (no prueba que alguien lo leyó)
    FALLIDO = "fallido"  # se agotaron los intentos o la falla es permanente


@dataclass(frozen=True)
class AvisoNuevo:
    destinatario: str
    mensaje: str


@dataclass
class Aviso:
    id: int
    reporte_codigo: str
    destinatario: str
    mensaje: str
    estado: EstadoAviso
    intentos: int
    creado_en: datetime
    proximo_intento_en: datetime
    enviado_en: datetime | None = None
    ultimo_error: str | None = None
