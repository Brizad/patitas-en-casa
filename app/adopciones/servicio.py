"""Casos de uso de la adopción (fase 3, #85): solicitar (RF-27, RN-10)."""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from app.adopciones.modelos import EstadoPublicacion, EstadoSolicitud, Solicitud
from app.adopciones.repositorio import RepositorioAdopciones
from app.dominio.modelos import Rol, Usuario


class PerfilIncompleto(ValueError):
    pass


class AnimalNoDisponible(LookupError):
    pass


class SolicitudRepetida(Exception):
    pass


class ServicioAdopciones:
    def __init__(self, repositorio: RepositorioAdopciones,
                 reloj: Callable[[], datetime] | None = None) -> None:
        self._repositorio = repositorio
        self._reloj = reloj or (lambda: datetime.now(UTC))

    def solicitar(self, adoptante: Usuario, animal_id: int, mensaje: str = "") -> Solicitud:
        if adoptante.rol != Rol.ADOPTANTE:
            raise PermissionError("Solo una cuenta de adoptante solicita adopciones.")
        perfil = self._repositorio.perfil(adoptante.correo)
        # RN-10: adoptante habilitado = perfil lleno y acepta el seguimiento (RF-10).
        if perfil is None or not perfil.habilitado():
            raise PerfilIncompleto("Completa tu perfil y acepta el seguimiento a los 30, 90 "
                                   "y 180 días para poder solicitar (RN-10).")
        publicacion = self._repositorio.publicacion(animal_id)
        if publicacion is None or publicacion.estado != EstadoPublicacion.DISPONIBLE:
            raise AnimalNoDisponible("Ese animal no está disponible para adopción.")
        solicitud = Solicitud(id=None, animal_id=animal_id, adoptante=adoptante.correo,
                              mensaje=mensaje.strip(), estado=EstadoSolicitud.PENDIENTE,
                              creada_en=self._reloj())
        if not self._repositorio.crear_solicitud(solicitud):
            raise SolicitudRepetida("Ya tienes una solicitud pendiente por este animal.")
        return solicitud
