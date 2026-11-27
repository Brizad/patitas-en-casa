"""#498: última posición del rescatista en camino (seguimiento en el mapa del ciudadano).

Revisión: 0039
Anterior: 0038
Fecha: 2026-11-28

Migración aditiva: crea la tabla ubicaciones_rescate (una fila por reporte, solo la última
posición; no es un historial). No toca ninguna tabla existente. La aplicación borra la fila
cuando el rescate sale de «en camino». El downgrade borra solo esta tabla nueva.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ubicaciones_rescate",
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  primary_key=True),
        sa.Column("latitud", sa.Double(), nullable=False),
        sa.Column("longitud", sa.Double(), nullable=False),
        sa.Column("simulada", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("actualizada_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("latitud BETWEEN -90 AND 90 AND longitud BETWEEN -180 AND 180",
                           name="ck_ubicaciones_rescate_rango"),
    )


def downgrade() -> None:
    op.drop_table("ubicaciones_rescate")
