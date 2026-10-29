"""Adopción en PostgreSQL (fase 3, #85)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Engine, func, select, update
from sqlalchemy import insert as insertar
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError

from app.adopciones.modelos import (
    ABIERTAS,
    Energia,
    EstadoPublicacion,
    EstadoSolicitud,
    PerfilAdoptante,
    Publicacion,
    Seguimiento,
    Solicitud,
    Tamano,
    Vivienda,
)
from app.bd.esquema import (
    animales,
    perfiles_adoptante,
    publicaciones,
    refugios,
    seguimientos,
    solicitudes,
)
from app.cupos.repositorio_postgres import SinCupo, reingresar_en
from app.dominio.modelos import MotivoEgreso

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
            return [_solicitud(f) for f in filas]

    def solicitud(self, solicitud_id: int) -> Solicitud | None:
        with self._motor.connect() as conexion:
            f = conexion.execute(select(solicitudes).where(
                solicitudes.c.id == solicitud_id)).mappings().first()
        return None if f is None else _solicitud(f)

    def rechazar(self, solicitud_id: int, por: str, razon: str, momento: datetime) -> bool:
        with self._motor.begin() as conexion:
            cambio = conexion.execute(update(solicitudes).where(
                solicitudes.c.id == solicitud_id,
                solicitudes.c.estado.in_([e.value for e in ABIERTAS])).values(
                estado=EstadoSolicitud.RECHAZADA.value, decidida_por=por, decidida_en=momento,
                razon=razon))
        return cambio.rowcount == 1

    def aprobar(self, solicitud_id: int, por: str, momento: datetime,
                seguimientos_nuevos: list[Seguimiento]) -> bool:
        """Una transacción. RN-11 la garantiza el índice único parcial: si dos coordinadores
        aprueban dos solicitudes del mismo animal a la vez, la segunda falla y no cambia nada."""
        try:
            with self._motor.begin() as conexion:
                fila = conexion.execute(update(solicitudes).where(
                    solicitudes.c.id == solicitud_id,
                    solicitudes.c.estado.in_([e.value for e in ABIERTAS])).values(
                    estado=EstadoSolicitud.APROBADA.value, decidida_por=por,
                    decidida_en=momento).returning(solicitudes.c.animal_id)).first()
                if fila is None:
                    return False
                animal_id = fila.animal_id
                conexion.execute(update(solicitudes).where(
                    solicitudes.c.animal_id == animal_id,
                    solicitudes.c.estado.in_([e.value for e in ABIERTAS])).values(
                    estado=EstadoSolicitud.RECHAZADA.value, decidida_por=por,
                    decidida_en=momento, razon="Se aprobó otra solicitud para este animal."))
                conexion.execute(update(publicaciones).where(
                    publicaciones.c.animal_id == animal_id).values(
                    estado=EstadoPublicacion.ADOPTADO.value))
                # Egreso por adopción y cupo libre (RF-26), en la misma transacción.
                refugio_id = conexion.execute(update(animales).where(
                    animales.c.id == animal_id, animales.c.egresado_en.is_(None)).values(
                    egresado_en=func.now(), motivo_egreso=MotivoEgreso.ADOPCION.value)
                    .returning(animales.c.refugio_id)).scalar()
                if refugio_id is not None:
                    conexion.execute(update(refugios).where(refugios.c.id == refugio_id)
                                     .values(ocupados=refugios.c.ocupados - 1))
                for s in seguimientos_nuevos:
                    s.id = conexion.execute(insertar(seguimientos).values(
                        solicitud_id=solicitud_id, dia=s.dia,
                        programado_para=s.programado_para).returning(seguimientos.c.id)
                    ).scalar_one()
        except IntegrityError:
            return False
        return True

    def seguimientos(self, solicitud_id: int) -> list[Seguimiento]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(seguimientos).where(
                seguimientos.c.solicitud_id == solicitud_id).order_by(seguimientos.c.dia)
            ).mappings()
            return [_seguimiento(f) for f in filas]

    def registrar_seguimiento(self, seguimiento_id: int, por: str, nota: str,
                              momento: datetime) -> Seguimiento | None:
        with self._motor.begin() as conexion:
            f = conexion.execute(update(seguimientos).where(
                seguimientos.c.id == seguimiento_id, seguimientos.c.realizado_en.is_(None))
                .values(realizado_en=momento, nota=nota, registrado_por=por)
                .returning(*seguimientos.c)).mappings().first()
        return None if f is None else _seguimiento(f)


def _seguimiento(f) -> Seguimiento:
    return Seguimiento(id=f["id"], solicitud_id=f["solicitud_id"], dia=f["dia"],
                       programado_para=f["programado_para"], realizado_en=f["realizado_en"],
                       nota=f["nota"], registrado_por=f["registrado_por"])

    def pedir_visita(self, solicitud_id: int, por: str, nota: str, momento: datetime) -> bool:
        with self._motor.begin() as conexion:
            cambio = conexion.execute(update(solicitudes).where(
                solicitudes.c.id == solicitud_id,
                solicitudes.c.estado == EstadoSolicitud.PENDIENTE.value).values(
                estado=EstadoSolicitud.VISITA.value, decidida_por=por, decidida_en=momento,
                razon=nota))
        return cambio.rowcount == 1

    def devolver(self, solicitud_id: int, por: str, motivo: str,
                 momento: datetime) -> bool | None:
        """Una transacción: si el animal no cabe (SinCupo), no cambia nada."""
        try:
            with self._motor.begin() as conexion:
                animal_id = conexion.execute(update(solicitudes).where(
                    solicitudes.c.id == solicitud_id,
                    solicitudes.c.estado == EstadoSolicitud.APROBADA.value).values(
                    estado=EstadoSolicitud.DEVUELTA.value, decidida_por=por,
                    decidida_en=momento, razon=motivo).returning(solicitudes.c.animal_id)
                ).scalar()
                if animal_id is None:
                    return False
                reingresar_en(conexion, animal_id)
                conexion.execute(update(publicaciones).where(
                    publicaciones.c.animal_id == animal_id).values(
                    estado=EstadoPublicacion.DISPONIBLE.value))
        except SinCupo:
            return None
        return True


def _solicitud(f) -> Solicitud:
    return Solicitud(id=f["id"], animal_id=f["animal_id"], adoptante=f["adoptante"],
                     mensaje=f["mensaje"], estado=EstadoSolicitud(f["estado"]),
                     creada_en=f["creada_en"], decidida_por=f["decidida_por"],
                     decidida_en=f["decidida_en"], razon=f["razon"])


def _publicacion(f) -> Publicacion:
    return Publicacion(
        animal_id=f["animal_id"], descripcion=f["descripcion"], tamano=Tamano(f["tamano"]),
        energia=Energia(f["energia"]), edad_meses=f["edad_meses"], apto_ninos=f["apto_ninos"],
        apto_otros_animales=f["apto_otros_animales"], necesita_patio=f["necesita_patio"],
        nombre=f["nombre"], especie=f["especie"], estado=EstadoPublicacion(f["estado"]),
        publicado_en=f["publicado_en"])
