"""Trabajos de análisis de video (#125, RF-03, RF-19).

Revisión: 0025
Anterior: 0024
Fecha: 2026-10-29

Un trabajo por reporte (codigo único). El video no se guarda aquí: vive en el disco temporal
de Render hasta que el trabajador local lo analiza; en la tabla quedan solo el estado, las
medidas, las evidencias y una tira pequeña de 3 cuadros (≤ 200 KB).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "analisis_video",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("codigo", sa.String(8), sa.ForeignKey("reportes.codigo"), nullable=False,
                  unique=True),
        sa.Column("ruta", sa.Text(), nullable=False),
        sa.Column("bytes", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(16), nullable=False),
        sa.Column("intentos", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reclamado_en", sa.DateTime(timezone=True)),
        sa.Column("terminado_en", sa.DateTime(timezone=True)),
        sa.Column("prioridad", sa.String(10)),
        sa.Column("confianza", sa.Double()),
        sa.Column("evidencias", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("medidas", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("version_modelo", sa.String(40)),
        sa.Column("motivo", sa.Text()),
        sa.Column("discrepancia", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tira", sa.LargeBinary()),
        sa.CheckConstraint("estado IN ('pendiente', 'enviado', 'terminado', 'no_concluyente', "
                           "'fallido')", name="ck_analisis_video_estado"),
        sa.CheckConstraint("bytes <= 52428800", name="ck_analisis_video_tamano"),
        sa.CheckConstraint("tira IS NULL OR octet_length(tira) <= 204800",
                           name="ck_analisis_video_tira"),
    )
    op.create_index("ix_analisis_video_estado_creado", "analisis_video", ["estado", "creado_en"])


def downgrade() -> None:
    op.drop_index("ix_analisis_video_estado_creado", table_name="analisis_video")
    op.drop_table("analisis_video")
