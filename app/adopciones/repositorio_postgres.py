"""Adopción en PostgreSQL (fase 3, #85)."""
from __future__ import annotations

from sqlalchemy import Engine, select
from sqlalchemy import insert as insertar
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.adopciones.modelos import (
    Energia,
    EstadoPublicacion,
    EstadoSolicitud,
    PerfilAdoptante,
    Publicacion,
    Solicitud,
    Tamano,
    Vivienda,
)
from app.bd.esquema import animales, perfiles_adoptante, publicaciones, solicitudes

# La publicación con el nombre y la especie de la ficha del animal.
_CONSULTA = select(publicaciones, animales.c.nombre, animales.c.especie).join(
    animales, animales.c.id == publicaciones.c.animal_id)


class RepositorioAdopcionesPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def guardar_perfil(self, perfil: PerfilAdoptante) -> None:
        fila = {"correo": perfil.correo, "vivienda": perfil.vivienda.value,
                "tiene_patio": perfil.tiene_patio, "hay_ninos": perfil.hay_ninos,
                "otros_animales": perfil.otros_animales,
                "horas_solo_al_dia": perfil.horas_solo_al_dia,
                "experiencia": perfil.experiencia,
                "acepta_seguimiento": perfil.acepta_seguimiento,
                "actualizado_en": perfil.actualizado_en}
        sentencia = insert(perfiles_adoptante).values(**fila)
        sentencia = sentencia.on_conflict_do_update(
            index_elements=[perfiles_adoptante.c.correo],
            set_={k: sentencia.excluded[k] for k in fila if k != "correo"})
        with self._motor.begin() as conexion:
            conexion.execute(sentencia)

    def perfil(self, correo: str) -> PerfilAdoptante | None:
        with self._motor.connect() as conexion:
            f = conexion.execute(select(perfiles_adoptante).where(
                perfiles_adoptante.c.correo == correo)).mappings().first()
        if f is None:
            return None
        return PerfilAdoptante(
            correo=f["correo"], vivienda=Vivienda(f["vivienda"]), tiene_patio=f["tiene_patio"],
            hay_ninos=f["hay_ninos"], otros_animales=f["otros_animales"],
            horas_solo_al_dia=f["horas_solo_al_dia"], experiencia=f["experiencia"],
            acepta_seguimiento=f["acepta_seguimiento"], actualizado_en=f["actualizado_en"])

    def publicar(self, publicacion: Publicacion) -> bool:
        # La llave primaria (animal_id) garantiza una publicación por animal, aunque dos
        # coordinadores publiquen a la vez.
        with self._motor.begin() as conexion:
            creada = conexion.execute(insert(publicaciones).values(
                animal_id=publicacion.animal_id, descripcion=publicacion.descripcion,
                tamano=publicacion.tamano.value, energia=publicacion.energia.value,
                edad_meses=publicacion.edad_meses, apto_ninos=publicacion.apto_ninos,
                apto_otros_animales=publicacion.apto_otros_animales,
                necesita_patio=publicacion.necesita_patio, estado=publicacion.estado.value,
                publicado_en=publicacion.publicado_en,
            ).on_conflict_do_nothing(index_elements=[publicaciones.c.animal_id])
                .returning(publicaciones.c.animal_id)).first()
        return creada is not None

    def publicacion(self, animal_id: int) -> Publicacion | None:
        with self._motor.connect() as conexion:
            f = conexion.execute(_CONSULTA.where(
                publicaciones.c.animal_id == animal_id)).mappings().first()
        return None if f is None else _publicacion(f)

    def disponibles(self) -> list[Publicacion]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(_CONSULTA.where(
                publicaciones.c.estado == EstadoPublicacion.DISPONIBLE.value)
                .order_by(publicaciones.c.publicado_en)).mappings()
            return [_publicacion(f) for f in filas]

    def crear_solicitud(self, solicitud: Solicitud) -> bool:
        try:
            with self._motor.begin() as conexion:
                solicitud.id = conexion.execute(insertar(solicitudes).values(
                    animal_id=solicitud.animal_id, adoptante=solicitud.adoptante,
                    mensaje=solicitud.mensaje, estado=solicitud.estado.value,
                    creada_en=solicitud.creada_en).returning(solicitudes.c.id)).scalar_one()
        except IntegrityError:
            return False  # índice único parcial: ya había una pendiente
        return True

    def solicitudes(self) -> list[Solicitud]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(solicitudes).order_by(solicitudes.c.id)).mappings()
            return [Solicitud(id=f["id"], animal_id=f["animal_id"], adoptante=f["adoptante"],
                              mensaje=f["mensaje"], estado=EstadoSolicitud(f["estado"]),
                              creada_en=f["creada_en"]) for f in filas]


def _publicacion(f) -> Publicacion:
    return Publicacion(
        animal_id=f["animal_id"], descripcion=f["descripcion"], tamano=Tamano(f["tamano"]),
        energia=Energia(f["energia"]), edad_meses=f["edad_meses"], apto_ninos=f["apto_ninos"],
        apto_otros_animales=f["apto_otros_animales"], necesita_patio=f["necesita_patio"],
        nombre=f["nombre"], especie=f["especie"], estado=EstadoPublicacion(f["estado"]),
        publicado_en=f["publicado_en"])
