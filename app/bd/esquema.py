"""Tablas de PostgreSQL (DT-01). Cada cambio aquí necesita una migración en migraciones/."""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    false,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.dominio.modelos import Especie, EstadoReporte, Prioridad


def _valores(enum) -> str:
    return ", ".join(f"'{miembro.value}'" for miembro in enum)


metadata = MetaData()

reportes = Table(
    "reportes",
    metadata,
    Column("codigo", String(8), primary_key=True),
    Column("descripcion", Text, nullable=False),
    Column("latitud", Double),
    Column("longitud", Double),
    Column("direccion", Text),
    Column("video_segundos", Integer),
    Column("estado", String(20), nullable=False),
    Column("prioridad", String(10)),
    Column("confianza", Double),
    Column("evidencias", JSONB, nullable=False, server_default=text("'[]'::jsonb")),
    Column("creado_en", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"estado IN ({_valores(EstadoReporte)})", name="ck_reportes_estado"),
    CheckConstraint(f"prioridad IN ({_valores(Prioridad)})", name="ck_reportes_prioridad"),
    CheckConstraint("confianza BETWEEN 0 AND 1", name="ck_reportes_confianza"),
    CheckConstraint("video_segundos >= 0", name="ck_reportes_video"),
    # RN-01: GPS completo o dirección escrita.
    CheckConstraint(
        "(latitud IS NOT NULL AND longitud IS NOT NULL) OR direccion IS NOT NULL",
        name="ck_reportes_ubicacion",
    ),
)

# DT-05: la ocupación vive en la base; el cupo se toma con un UPDATE condicional (RN-04).
refugios = Table(
    "refugios",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("nombre", Text, nullable=False),
    Column("capacidad", Integer, nullable=False),
    Column("ocupados", Integer, nullable=False, server_default=text("0")),
    CheckConstraint("capacidad > 0", name="ck_refugios_capacidad"),
    CheckConstraint("ocupados BETWEEN 0 AND capacidad", name="ck_refugios_ocupados"),
)

animales = Table(
    "animales",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("refugio_id", Integer, ForeignKey("refugios.id"), nullable=False),
    Column("nombre", Text, nullable=False),
    Column("especie", String(10), nullable=False),
    Column("estado_salud", Text, nullable=False),
    Column("vacunado", Boolean, nullable=False, server_default=false()),
    Column("esterilizado", Boolean, nullable=False, server_default=false()),
    Column("ingresado_en", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint(f"especie IN ({_valores(Especie)})", name="ck_animales_especie"),
)
