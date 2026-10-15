"""Crear las tablas refugios y animales (DT-05).

Revisión: 0002
Anterior: 0001
Fecha: 2026-10-15

Deja creado el refugio demo (40 cupos) que antes se armaba en memoria en crear_app().
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    refugios = op.create_table(
        "refugios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("capacidad", sa.Integer(), nullable=False),
        sa.Column("ocupados", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint("capacidad > 0", name="ck_refugios_capacidad"),
        sa.CheckConstraint("ocupados BETWEEN 0 AND capacidad", name="ck_refugios_ocupados"),
    )
    op.create_table(
        "animales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("refugio_id", sa.Integer(), sa.ForeignKey("refugios.id"), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("especie", sa.String(10), nullable=False),
        sa.Column("estado_salud", sa.Text(), nullable=False),
        sa.Column("vacunado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("esterilizado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ingresado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint("especie IN ('perro', 'gato')", name="ck_animales_especie"),
    )
    op.bulk_insert(refugios, [{"nombre": "Refugio demo Cúcuta", "capacidad": 40}])


def downgrade() -> None:
    op.drop_table("animales")
    op.drop_table("refugios")
