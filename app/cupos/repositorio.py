"""Persistencia de los cupos del refugio (DT-05)."""
from __future__ import annotations

import threading
from dataclasses import replace
from datetime import UTC, datetime
from typing import Protocol

from app.dominio.modelos import Animal, MotivoEgreso, NotaClinica, Refugio


class RepositorioCupos(Protocol):
    def refugio(self) -> Refugio: ...

    def para_refugio(self, refugio_id: int) -> RepositorioCupos:
        """El mismo almacenamiento, apuntando a otro refugio (#75)."""
        ...

    def ocupar_cupo(self, animal: Animal) -> Refugio | None:
        """Comprueba el cupo, lo ocupa y guarda el animal en una sola operación.

        Devuelve el refugio actualizado, o None si no había cupo (nada cambia). Asigna
        animal.id y animal.ingresado_en (#75).
        """
        ...

    def animales(self) -> list[Animal]:
        """Fichas de los animales de ESTE refugio, por orden de ingreso (RF-06)."""
        ...

    def animal(self, animal_id: int) -> Animal | None:
        """None si no existe o es de otro refugio."""
        ...

    def agregar_nota(self, nota: NotaClinica) -> None: ...

    def egresar(self, animal_id: int, motivo: MotivoEgreso) -> Refugio | None:
        """RF-26: marca el egreso y libera el cupo en una sola operación. None si el animal
        no está en este refugio o ya egresó (nada cambia)."""
        ...

    def historial(self, animal_id: int) -> list[NotaClinica]: ...


class RepositorioCuposEnMemoria:
    def __init__(self, refugio: Refugio) -> None:
        self._refugio = refugio
        self._animales: list[Animal] = []
        self._notas: list[NotaClinica] = []
        # BUG-04: comprobar el cupo y ocuparlo es una sola operación (un solo proceso).
        self._candado = threading.Lock()

    def refugio(self) -> Refugio:
        return replace(self._refugio)

    def para_refugio(self, refugio_id: int) -> RepositorioCuposEnMemoria:
        # En memoria hay un solo refugio (pruebas): todos los vínculos apuntan a él.
        return self

    def ocupar_cupo(self, animal: Animal) -> Refugio | None:
        with self._candado:
            if not self._refugio.tiene_cupo():
                return None
            animal.id = len(self._animales) + 1
            animal.ingresado_en = datetime.now(UTC)
            self._animales.append(animal)
            self._refugio.ocupados += 1
            return replace(self._refugio)

    def animales(self) -> list[Animal]:
        return [replace(a) for a in self._animales]

    def animal(self, animal_id: int) -> Animal | None:
        return next((replace(a) for a in self._animales if a.id == animal_id), None)

    def agregar_nota(self, nota: NotaClinica) -> None:
        self._notas.append(nota)

    def egresar(self, animal_id: int, motivo: MotivoEgreso) -> Refugio | None:
        with self._candado:
            animal = next((a for a in self._animales if a.id == animal_id), None)
            if animal is None or animal.egresado_en is not None:
                return None
            animal.egresado_en, animal.motivo_egreso = datetime.now(UTC), motivo
            self._refugio.ocupados -= 1
            return replace(self._refugio)

    def historial(self, animal_id: int) -> list[NotaClinica]:
        return [n for n in self._notas if n.animal_id == animal_id]
