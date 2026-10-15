"""Persistencia de los cupos del refugio (DT-05)."""
from __future__ import annotations

import threading
from dataclasses import replace
from typing import Protocol

from app.dominio.modelos import Animal, Refugio


class RepositorioCupos(Protocol):
    def refugio(self) -> Refugio: ...

    def ocupar_cupo(self, animal: Animal) -> Refugio | None:
        """Comprueba el cupo, lo ocupa y guarda el animal en una sola operación.

        Devuelve el refugio actualizado, o None si no había cupo (nada cambia).
        """
        ...


class RepositorioCuposEnMemoria:
    def __init__(self, refugio: Refugio) -> None:
        self._refugio = refugio
        self.animales: list[Animal] = []
        # BUG-04: comprobar el cupo y ocuparlo es una sola operación (un solo proceso).
        self._candado = threading.Lock()

    def refugio(self) -> Refugio:
        return replace(self._refugio)

    def ocupar_cupo(self, animal: Animal) -> Refugio | None:
        with self._candado:
            if not self._refugio.tiene_cupo():
                return None
            self.animales.append(animal)
            self._refugio.ocupados += 1
            return replace(self._refugio)
