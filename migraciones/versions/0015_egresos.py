"""Egresos de animales (fase 2, #75, RF-26).

Revisión: 0015
Anterior: 0014
Fecha: 2026-10-29

Dos columnas opcionales en animales: los animales actuales quedan «en el refugio» (NULL).
Un CHECK exige que fecha y motivo vayan juntos.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("animales", sa.Column("egresado_en", sa.DateTime(timezone=True)))
    op.add_column("animales", sa.Column("motivo_egreso", sa.String(15)))
    op.create_check_constraint(
        "ck_animales_motivo_egreso", "animales",
        "motivo_egreso IN ('adopcion', 'traslado', 'fallecimiento', 'devuelto')")
    op.create_check_constraint("ck_animales_egreso_completo", "animales",
                               "(egresado_en IS NULL) = (motivo_egreso IS NULL)")


def downgrade() -> None:
    op.drop_constraint("ck_animales_egreso_completo", "animales", type_="check")
    op.drop_constraint("ck_animales_motivo_egreso", "animales", type_="check")
    op.drop_column("animales", "motivo_egreso")
    op.drop_column("animales", "egresado_en")
