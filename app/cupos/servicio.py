"""Gestión de cupos del refugio (RF-06 y RF-07)."""
from __future__ import annotations

from typing import Protocol

from app import config
from app.dominio.modelos import Animal, Refugio


class Notificador(Protocol):
    def enviar(self, destinatario: str, mensaje: str) -> None: ...


class CupoAgotado(Exception):
    pass


class ServicioCupos:
    def __init__(self, refugio: Refugio, notificador: Notificador) -> None:
        self._refugio = refugio
        self._notificador = notificador
        self.animales: list[Animal] = []

    def registrar_ingreso(self, animal: Animal) -> Refugio:
        if not animal.nombre or not animal.estado_salud:
            raise ValueError("La ficha clínica exige nombre y estado de salud.")
        if self._refugio.ocupados >= self._refugio.capacidad:
            raise CupoAgotado(f"{self._refugio.nombre} no tiene cupos disponibles.")
        self.animales.append(animal)
        self._refugio.ocupados += 1
        if self.porcentaje_ocupacion() >= config.ALERTA_OCUPACION:
            self._notificador.enviar(
                "coordinadores",
                f"Ocupación sobre el {int(config.ALERTA_OCUPACION * 100)} % en {self._refugio.nombre}",
            )
        return self._refugio

    def porcentaje_ocupacion(self) -> float:
        # Calcula con los datos internos del refugio.
        return self._refugio.ocupados / self._refugio.capacidad

    def texto_ocupacion(self) -> str:
        return f"{self._refugio.ocupados}/{self._refugio.capacidad}"
