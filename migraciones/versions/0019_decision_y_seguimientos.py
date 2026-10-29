"""Decisión de la solicitud y seguimientos (fase 3, #85, RF-27, RN-11, RF-10).

Revisión: 0019
Anterior: 0018
Fecha: 2026-10-29

Columnas opcionales de la decisión en solicitudes, un índice único parcial que permite una
sola solicitud aprobada por animal (RN-11) y la tabla de seguimientos a 30, 90 y 180 días.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("solicitudes", sa.Column("decidida_por", sa.Text()))
    op.add_column("solicitudes", sa.Column("decidida_en", sa.DateTime(timezone=True)))
    op.add_column("solicitudes", sa.Column("razon", sa.Text()))
    op.create_index("uq_solicitudes_aprobada", "solicitudes", ["animal_id"], unique=True,
                    postgresql_where=sa.text("estado = 'aprobada'"))
    op.create_table(
        "seguimientos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("solicitud_id", sa.Integer(), sa.ForeignKey("solicitudes.id"),
                  nullable=False),
        sa.Column("dia", sa.SmallInteger(), nullable=False),
        sa.Column("programado_para", sa.DateTime(timezone=True), nullable=False),
        sa.Column("realizado_en", sa.DateTime(timezone=True)),
        sa.Column("nota", sa.Text()),
        sa.Column("registrado_por", sa.Text()),
        sa.CheckConstraint("dia IN (30, 90, 180)", name="ck_seguimientos_dia"),
        sa.UniqueConstraint("solicitud_id", "dia", name="uq_seguimientos_dia"),
    )


def downgrade() -> None:
    op.drop_table("seguimientos")
    op.drop_index("uq_solicitudes_aprobada", table_name="solicitudes")
    op.drop_column("solicitudes", "razon")
    op.drop_column("solicitudes", "decidida_en")
    op.drop_column("solicitudes", "decidida_por")
