"""RepositorioPiloto en PostgreSQL (#258)."""
from __future__ import annotations

from dataclasses import asdict

from sqlalchemy import Engine, func, select, update
from sqlalchemy.dialects.postgresql import insert

from app.bd.esquema import piloto as tabla
from app.piloto.servicio import Participante


def _a_participante(f) -> Participante:
    return Participante(f["codigo"], f["token_hash"], f["creado_en"], f["vence_en"],
                        f["reporte_en"], f["segundos"],
                        list(f["sus"]) if f["sus"] is not None else None, f["respondido_en"])


class RepositorioPilotoPostgres:
    def __init__(self, motor: Engine) -> None:
        self._motor = motor

    def crear(self, participante: Participante) -> bool:
        sentencia = (insert(tabla).values(**asdict(participante))
                     .on_conflict_do_nothing(index_elements=[tabla.c.codigo])
                     .returning(tabla.c.codigo))
        with self._motor.begin() as conexion:
            return conexion.execute(sentencia).first() is not None

    def cuantos(self) -> int:
        with self._motor.connect() as conexion:
            return conexion.execute(select(func.count()).select_from(tabla)).scalar_one()

    def por_token(self, token_hash: str) -> Participante | None:
        with self._motor.connect() as conexion:
            fila = conexion.execute(select(tabla).where(tabla.c.token_hash == token_hash)
                                    ).mappings().first()
        return _a_participante(fila) if fila else None

    def guardar(self, participante: Participante) -> None:
        with self._motor.begin() as conexion:
            conexion.execute(update(tabla).where(tabla.c.codigo == participante.codigo)
                             .values(**asdict(participante)))

    def todos(self) -> list[Participante]:
        with self._motor.connect() as conexion:
            filas = conexion.execute(select(tabla).order_by(tabla.c.codigo)).mappings().all()
        return [_a_participante(f) for f in filas]
