"""Solicitudes de adopción (fase 3, #85, RF-27).

Revisión: 0018
Anterior: 0017
Fecha: 2026-10-29

Un índice único parcial impide dos solicitudes pendientes del mismo adoptante por el mismo
animal (un doble clic no crea dos).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "solicitudes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("publicaciones.animal_id"),
                  nullable=False),
        sa.Column("adoptante", sa.Text(), sa.ForeignKey("usuarios.correo"), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False, server_default=""),
        sa.Column("estado", sa.String(10), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("estado IN ('pendiente', 'aprobada', 'rechazada')",
                           name="ck_solicitudes_estado"),
    )
    op.create_index("uq_solicitudes_pendiente", "solicitudes", ["animal_id", "adoptante"],
                    unique=True, postgresql_where=sa.text("estado = 'pendiente'"))


def downgrade() -> None:
    op.drop_index("uq_solicitudes_pendiente", table_name="solicitudes")
    op.drop_table("solicitudes")
