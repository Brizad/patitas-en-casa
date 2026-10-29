"""Historial clínico de los animales (fase 2, #75, RF-06 y RF-24).

Revisión: 0014
Anterior: 0013
Fecha: 2026-10-29

Una tabla nueva (cambio compatible). Las notas solo se insertan: la aplicación no tiene
forma de editarlas ni borrarlas.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "historial_clinico",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("animal_id", sa.Integer(), sa.ForeignKey("animales.id"), nullable=False),
        sa.Column("autor", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(15), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("tipo IN ('observacion', 'tratamiento', 'vacuna', 'procedimiento')",
                           name="ck_historial_tipo"),
        sa.CheckConstraint("btrim(texto) <> ''", name="ck_historial_texto"),
    )
    op.create_index("ix_historial_clinico_animal", "historial_clinico", ["animal_id"])


def downgrade() -> None:
    op.drop_index("ix_historial_clinico_animal", table_name="historial_clinico")
    op.drop_table("historial_clinico")
