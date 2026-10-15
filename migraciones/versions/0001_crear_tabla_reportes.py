"""Crear la tabla reportes (DT-01).

Revisión: 0001
Anterior: ninguna
Fecha: 2026-10-14

Los valores de estado y prioridad se copian aquí a propósito: una migración describe la
base en un momento dado y no debe cambiar si mañana cambia el código del dominio.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reportes",
        sa.Column("codigo", sa.String(8), primary_key=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("latitud", sa.Double()),
        sa.Column("longitud", sa.Double()),
        sa.Column("direccion", sa.Text()),
        sa.Column("video_segundos", sa.Integer()),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("prioridad", sa.String(10)),
        sa.Column("confianza", sa.Double()),
        sa.Column("evidencias", postgresql.JSONB(), nullable=False,
                  server_default=sa.text("'[]'::jsonb")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "estado IN ('recibido', 'clasificado', 'requiere_revision', 'sin_clasificar', "
            "'confirmado')",
            name="ck_reportes_estado",
        ),
        sa.CheckConstraint("prioridad IN ('critica', 'alta', 'media', 'baja')",
                           name="ck_reportes_prioridad"),
        sa.CheckConstraint("confianza BETWEEN 0 AND 1", name="ck_reportes_confianza"),
        sa.CheckConstraint("video_segundos >= 0", name="ck_reportes_video"),
        sa.CheckConstraint(
            "(latitud IS NOT NULL AND longitud IS NOT NULL) OR direccion IS NOT NULL",
            name="ck_reportes_ubicacion",
        ),
    )


def downgrade() -> None:
    op.drop_table("reportes")
