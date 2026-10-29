"""Ficha clínica e historial de los animales del refugio (RF-06, RF-24, #75)."""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.cupos.repositorio import RepositorioCupos
from app.dominio.modelos import NotaClinica, Rol, TipoNota, Usuario

MIN_LETRAS_NOTA = 3


class NotaInvalida(ValueError):
    pass


class AnimalNoEncontrado(LookupError):
    pass


class ServicioFichas:
    def __init__(self, repositorio: RepositorioCupos,
                 reloj: Callable[[], datetime] | None = None) -> None:
        self._repositorio = repositorio
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def agregar_nota(self, animal_id: int, autor: Usuario, tipo: TipoNota,
                     texto: str) -> NotaClinica:
        """El historial solo crece: no hay editar ni borrar. Si una nota está mal, se agrega
        otra que la corrige, y así queda la traza de quién dijo qué y cuándo (RF-32)."""
        if autor.rol != Rol.VETERINARIO:
            raise PermissionError("Solo el veterinario escribe en la ficha clínica.")
        texto = texto.strip()
        if sum(letra.isalpha() for letra in texto) < MIN_LETRAS_NOTA:
            raise NotaInvalida("Escribe la nota con palabras.")
        # El repositorio solo ve los animales de su refugio: uno de otro refugio «no existe».
        if self._repositorio.animal(animal_id) is None:
            raise AnimalNoEncontrado(f"No hay un animal {animal_id} en este refugio.")
        nota = NotaClinica(animal_id=animal_id, autor=autor.correo, tipo=tipo, texto=texto,
                           registrada_en=self._reloj())
        self._repositorio.agregar_nota(nota)
        return nota
