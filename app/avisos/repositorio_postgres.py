"""RepositorioAvisos en PostgreSQL (#63, outbox)."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import Connection, Engine, and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.avisos.modelos import Aviso, AvisoNuevo, EstadoAviso
from app.bd.esquema import avisos as tabla


def insertar_avisos(conexion: Connection, codigo: str, avisos: Sequence[AvisoNuevo],
                    ahora: datetime) -> int:
    """Usa la conexión de quien llama: así la confirmación y sus avisos quedan en la misma
    transacción. Los repetidos (mismo reporte y destinatario) se ignoran."""
    if not avisos:
        return 0
    filas = [{"reporte_codigo": codigo, "destinatario": a.destinatario, "mensaje": a.mensaje,
              "estado": EstadoAviso.PENDIENTE.value, "creado_en": ahora,
              "proximo_intento_en": ahora} for a in avisos]
    resultado = conexion.execute(insert(tabla).values(filas).on_conflict_do_nothing(
        constraint="uq_avisos_reporte_destinatario").returning(tabla.c.id))
    return len(resultado.all())


def _a_aviso(fila) -> Aviso:
    return Aviso(fila["id"], fila["reporte_codigo"], fila["destinatario"], fila["mensaje"],
                 EstadoAviso(fila["estado"]), fila["intentos"], fila["creado_en"],
                 fila["proximo_intento_en"], fila["enviado_en"], fila["ultimo_error"],
                 fila["reclamado_en"])


class RepositorioAvisosPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def agregar(self, codigo: str, avisos: Sequence[AvisoNuevo], ahora: datetime) -> int:
        with self._motor.begin() as conexion:
            return insertar_avisos(conexion, codigo, avisos, ahora)

    def reclamar(self, ahora: datetime, limite: int, vencimiento: timedelta) -> list[Aviso]:
        """SKIP LOCKED: si otro procesador tiene bloqueada una fila, esta consulta la salta en
        vez de esperarla, y ningún aviso se reclama dos veces a la vez."""
        listos = (select(tabla.c.id)
                  .where(or_(and_(tabla.c.estado == EstadoAviso.PENDIENTE.value,
                                  tabla.c.proximo_intento_en <= ahora),
                             and_(tabla.c.estado == EstadoAviso.ENVIANDO.value,
                                  tabla.c.reclamado_en < ahora - vencimiento)))
                  .order_by(tabla.c.id).limit(limite)
                  .with_for_update(skip_locked=True))
        sentencia = (update(tabla).where(tabla.c.id.in_(listos.scalar_subquery()))
                     .values(estado=EstadoAviso.ENVIANDO.value, reclamado_en=ahora,
                             intentos=tabla.c.intentos + 1)
                     .returning(*tabla.c))
        with self._motor.begin() as conexion:
            filas = conexion.execute(sentencia).mappings().all()
        return sorted((_a_aviso(f) for f in filas), key=lambda a: a.id)

    def marcar_enviado(self, aviso_id: int, ahora: datetime) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(update(tabla).where(tabla.c.id == aviso_id).values(
                estado=EstadoAviso.ENVIADO.value, enviado_en=ahora, ultimo_error=None))

    def marcar_fallo(self, aviso_id: int, error: str, proximo: datetime | None) -> None:
        cambios = ({"estado": EstadoAviso.FALLIDO.value} if proximo is None else
                   {"estado": EstadoAviso.PENDIENTE.value, "proximo_intento_en": proximo})
        with self._motor.begin() as conexion:
            conexion.execute(update(tabla).where(tabla.c.id == aviso_id).values(
                ultimo_error=error, **cambios))

    def de_reporte(self, codigo: str) -> list[Aviso]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(tabla).where(tabla.c.reporte_codigo == codigo)
                                     .order_by(tabla.c.id)).mappings().all()
        return [_a_aviso(f) for f in filas]
