"""Modo piloto de usabilidad (RNF-06, #258).

El administrador invita a un participante anónimo (P01, P02…) y le abre la PWA con un token de
un solo uso. En modo piloto el reporte se valida con las mismas reglas que uno real (RN-01),
pero **no se guarda como reporte**: nunca llega a la cola ni a los rescatistas. Solo se guardan
los segundos (del primer toque al código) y las 10 respuestas del SUS, sin datos personales.
"""
from __future__ import annotations

import csv
import hashlib
import io
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol

from app import config
from app.dominio.modelos import Ubicacion
from app.reportes.servicio import ServicioReportes, generar_codigo

PREGUNTAS_SUS = 10
MAX_SEGUNDOS = 3600


class PilotoRechazado(Exception):
    def __init__(self, estado_http: int, mensaje: str) -> None:
        super().__init__(mensaje)
        self.estado_http = estado_http


@dataclass
class Participante:
    codigo: str  # P01, P02… nunca un nombre
    token_hash: str
    creado_en: datetime
    vence_en: datetime
    reporte_en: datetime | None = None  # cuándo recibió el código del reporte de prueba
    segundos: int | None = None
    sus: list[int] | None = None
    respondido_en: datetime | None = None


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def puntaje_sus(respuestas: list[int]) -> float:
    """Impares (frases positivas) r-1, pares 5-r; la suma por 2,5 da 0 a 100."""
    return sum((r - 1) if i % 2 == 0 else (5 - r) for i, r in enumerate(respuestas)) * 2.5


class RepositorioPiloto(Protocol):
    def crear(self, participante: Participante) -> bool:
        """False si el código ya existe (otro administrador invitó al mismo tiempo)."""
        ...

    def cuantos(self) -> int: ...
    def por_token(self, token_hash: str) -> Participante | None: ...
    def guardar(self, participante: Participante) -> None: ...
    def todos(self) -> list[Participante]: ...


class RepositorioPilotoEnMemoria:
    def __init__(self) -> None:
        self._datos: dict[str, Participante] = {}
        self._candado = threading.Lock()

    def crear(self, participante: Participante) -> bool:
        with self._candado:
            if participante.codigo in self._datos:
                return False
            self._datos[participante.codigo] = participante
            return True

    def cuantos(self) -> int:
        return len(self._datos)

    def por_token(self, token_hash: str) -> Participante | None:
        return next((p for p in self._datos.values() if p.token_hash == token_hash), None)

    def guardar(self, participante: Participante) -> None:
        self._datos[participante.codigo] = participante

    def todos(self) -> list[Participante]:
        return sorted(self._datos.values(), key=lambda p: p.codigo)


class ServicioPiloto:
    def __init__(self, repositorio: RepositorioPiloto,
                 reloj: Callable[[], datetime] | None = None) -> None:
        self._repositorio = repositorio
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def invitar(self) -> tuple[Participante, str]:
        """Nuevo participante anónimo y su token (solo se guarda el hash)."""
        ahora = self._reloj()
        while True:
            token = secrets.token_urlsafe(18)
            p = Participante(f"P{self._repositorio.cuantos() + 1:02d}", hash_token(token), ahora,
                             ahora + timedelta(hours=config.PILOTO_HORAS_VIGENCIA))
            if self._repositorio.crear(p):
                return p, token

    def _activo(self, token: str | None) -> Participante:
        p = self._repositorio.por_token(hash_token(token)) if token else None
        if p is None or self._reloj() > p.vence_en:
            raise PilotoRechazado(403, "Este enlace de prueba no es válido o ya venció.")
        if p.respondido_en is not None:
            raise PilotoRechazado(409, "Esta prueba ya terminó. ¡Gracias por participar!")
        return p

    def reportar(self, token: str | None, descripcion: str, ubicacion: Ubicacion,
                 video_segundos: int | None = None, video_mb: float | None = None) -> str:
        """Valida como un reporte real y devuelve un código; no guarda ningún reporte."""
        p = self._activo(token)
        ServicioReportes.validar(descripcion, ubicacion, video_segundos, video_mb)
        p.reporte_en = self._reloj()
        self._repositorio.guardar(p)
        return generar_codigo()

    def responder(self, token: str | None, segundos: int, respuestas: list[int]) -> Participante:
        p = self._activo(token)
        if p.reporte_en is None:
            raise PilotoRechazado(409, "Primero envía el reporte de prueba.")
        if not 0 < segundos <= MAX_SEGUNDOS:
            raise PilotoRechazado(422, "El tiempo debe estar entre 1 segundo y 1 hora.")
        if len(respuestas) != PREGUNTAS_SUS or any(not 1 <= r <= 5 for r in respuestas):
            raise PilotoRechazado(422, "Responde las 10 frases con un número del 1 al 5.")
        p.segundos, p.sus, p.respondido_en = segundos, list(respuestas), self._reloj()
        self._repositorio.guardar(p)
        return p

    def completos(self) -> list[Participante]:
        return [p for p in self._repositorio.todos() if p.respondido_en is not None]

    def invitados(self) -> int:
        return self._repositorio.cuantos()

    def csv(self) -> str:
        """Mismo formato que docs/piloto/plantilla.csv (scripts/operacion/resultados_piloto.py)."""
        salida = io.StringIO()
        escritor = csv.writer(salida, lineterminator="\n")
        escritor.writerow(["participante", "segundos",
                           *[f"sus_{i}" for i in range(1, PREGUNTAS_SUS + 1)]])
        for p in self.completos():
            escritor.writerow([p.codigo, p.segundos, *p.sus])
        return salida.getvalue()
