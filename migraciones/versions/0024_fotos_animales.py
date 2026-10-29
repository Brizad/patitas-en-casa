"""Fotos de los animales en adopción (#115, RF-25).

Revisión: 0024
Anterior: 0023
Fecha: 2026-10-29

Una foto por animal (llave primaria), guardada en la base porque el disco de Render gratis
no persiste. El CHECK limita el tamaño a 300 KB aunque el código fallara.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fotos_animales",
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animales.id"), primary_key=True),
        sa.Column("tipo", sa.String(12), nullable=False),
        sa.Column("datos", sa.LargeBinary(), nullable=False),
        sa.Column("guardada_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo IN ('image/jpeg', 'image/png', 'image/webp')",
                           name="ck_fotos_tipo"),
        sa.CheckConstraint("octet_length(datos) <= 307200", name="ck_fotos_tamano"),
    )


def downgrade() -> None:
    op.drop_table("fotos_animales")
