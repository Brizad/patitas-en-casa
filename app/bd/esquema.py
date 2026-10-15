"""Tablas de PostgreSQL (DT-01). Cada cambio aquí necesita una migración en migraciones/."""
from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Double,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.dominio.modelos import EstadoReporte, Prioridad


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
