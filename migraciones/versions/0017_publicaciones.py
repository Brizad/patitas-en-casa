"""Animales publicados para adopción (fase 3, #85, RF-25).

Revisión: 0017
Anterior: 0016
Fecha: 2026-10-29

Una tabla nueva; la llave primaria animal_id permite una sola publicación por animal.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "publicaciones",
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animales.id"), primary_key=True),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("tamano", sa.String(10), nullable=False),
        sa.Column("energia", sa.String(10), nullable=False),
        sa.Column("edad_meses", sa.SmallInteger(), nullable=False),
        sa.Column("apto_ninos", sa.Boolean(), nullable=False),
        sa.Column("apto_otros_animales", sa.Boolean(), nullable=False),
        sa.Column("necesita_patio", sa.Boolean(), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("publicado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tamano IN ('pequeno', 'mediano', 'grande')",
                           name="ck_publicaciones_tamano"),
        sa.CheckConstraint("energia IN ('baja', 'media', 'alta')",
                           name="ck_publicaciones_energia"),
        sa.CheckConstraint("estado IN ('disponible', 'adoptado')",
                           name="ck_publicaciones_estado"),
        sa.CheckConstraint("edad_meses BETWEEN 0 AND 360", name="ck_publicaciones_edad"),
    )


def downgrade() -> None:
    op.drop_table("publicaciones")
