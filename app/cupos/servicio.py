"""Gestión de cupos del refugio (RF-06 y RF-07)."""
from __future__ import annotations

from typing import Protocol

from app import config
from app.cupos.repositorio import RepositorioCupos, RepositorioCuposEnMemoria
from app.dominio.modelos import Animal, Refugio


class Notificador(Protocol):
    def enviar(self, destinatario: str, mensaje: str) -> None: ...


class CupoAgotado(Exception):
    pass


class ServicioCupos:
    def __init__(self, repositorio: RepositorioCupos | Refugio, notificador: Notificador) -> None:
        # Un Refugio suelto se guarda en memoria (pruebas unitarias y compatibilidad).
        if isinstance(repositorio, Refugio):
            repositorio = RepositorioCuposEnMemoria(repositorio)
        self._repositorio = repositorio
        self._notificador = notificador

    def registrar_ingreso(self, animal: Animal) -> Refugio:
        if not animal.nombre or not animal.estado_salud:
            raise ValueError("La ficha clínica exige nombre y estado de salud.")
        refugio = self._repositorio.ocupar_cupo(animal)
        if refugio is None:
            nombre = self._repositorio.refugio().nombre
            raise CupoAgotado(f"{nombre} no tiene cupos disponibles.")
        if refugio.porcentaje_ocupacion() >= config.ALERTA_OCUPACION:
            umbral = int(config.ALERTA_OCUPACION * 100)
            self._notificador.enviar(
                "coordinadores", f"Ocupación sobre el {umbral} % en {refugio.nombre}"
            )
        return refugio

    def porcentaje_ocupacion(self) -> float:
        return self._repositorio.refugio().porcentaje_ocupacion()

    def texto_ocupacion(self) -> str:
        return self._repositorio.refugio().texto_ocupacion()
