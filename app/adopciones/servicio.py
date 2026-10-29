"""Casos de uso de la adopción (fase 3, #85): solicitar y decidir (RF-27, RN-05, RN-10,
RN-11) y programar los seguimientos (RF-10)."""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from app.adopciones.modelos import (
    DIAS_SEGUIMIENTO,
    EstadoPublicacion,
    EstadoSolicitud,
    Seguimiento,
    Solicitud,
)
from app.adopciones.reglas import restricciones_duras
from app.adopciones.repositorio import RepositorioAdopciones
from app.dominio.modelos import Rol, Usuario
from app.reportes.confirmacion import validar_justificacion


class PerfilIncompleto(ValueError):
    pass


class AnimalNoDisponible(LookupError):
    pass


class SolicitudRepetida(Exception):
    pass


class SolicitudNoEncontrada(LookupError):
    pass


class SolicitudYaDecidida(Exception):
    pass


class RestriccionDura(ValueError):
    pass


class RazonInvalida(ValueError):
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

    def decidir(self, coordinador: Usuario, solicitud_id: int, aprobar: bool,
                razon: str | None = None) -> Solicitud:
        """RF-27. Rechazar exige una razón (como RN-16, sin relleno: D-07). Aprobar no se
        permite si hay una restricción dura (RN-05) y programa los seguimientos (RF-10)."""
        if coordinador.rol != Rol.COORDINADOR:
            raise PermissionError("Solo el coordinador decide las adopciones.")
        solicitud = self._repositorio.solicitud(solicitud_id)
        if solicitud is None:
            raise SolicitudNoEncontrada(f"No existe la solicitud {solicitud_id}.")
        if solicitud.estado != EstadoSolicitud.PENDIENTE:
            raise SolicitudYaDecidida("Esta solicitud ya fue decidida.")
        ahora = self._reloj()
        if not aprobar:
            razon = (razon or "").strip()
            validar_justificacion(razon, RazonInvalida)
            if not self._repositorio.rechazar(solicitud_id, coordinador.correo, razon, ahora):
                raise SolicitudYaDecidida("Esta solicitud ya fue decidida.")
            return self._repositorio.solicitud(solicitud_id)
        perfil = self._repositorio.perfil(solicitud.adoptante)
        publicacion = self._repositorio.publicacion(solicitud.animal_id)
        motivos = restricciones_duras(perfil, publicacion)
        if motivos:
            raise RestriccionDura("No se puede aprobar (RN-05): " + "; ".join(motivos) + ".")
        plan = [Seguimiento(None, solicitud_id, dia, ahora + timedelta(days=dia))
                for dia in DIAS_SEGUIMIENTO]
        if not self._repositorio.aprobar(solicitud_id, coordinador.correo, ahora, plan):
            raise SolicitudYaDecidida("Este animal ya tiene una adopción aprobada (RN-11).")
        return self._repositorio.solicitud(solicitud_id)
