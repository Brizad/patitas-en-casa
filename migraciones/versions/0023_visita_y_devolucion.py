"""Visita previa y devolución en las solicitudes de adopción (#113, RF-27, RF-10, RN-13).

Revisión: 0023
Anterior: 0022
Fecha: 2026-10-29

Solo amplía el CHECK de estados: «visita» (el refugio pidió visitar el hogar antes de
decidir) y «devuelta» (el animal volvió al refugio). Bajar la revisión falla si ya hay
solicitudes en esos estados: no se cambian en silencio.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_solicitudes_estado", "solicitudes", type_="check")
    op.create_check_constraint(
        "ck_solicitudes_estado", "solicitudes",
        "estado IN ('pendiente', 'visita', 'aprobada', 'rechazada', 'devuelta')")


def downgrade() -> None:
    op.drop_constraint("ck_solicitudes_estado", "solicitudes", type_="check")
    op.create_check_constraint("ck_solicitudes_estado", "solicitudes",
                               "estado IN ('pendiente', 'aprobada', 'rechazada')")
