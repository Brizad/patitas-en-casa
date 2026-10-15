"""Zona por comunas y escalamiento de rescates (HU-06, parte 2, #57).

Revisión: 0007
Anterior: 0006
Fecha: 2026-10-15

Agrega la comuna del reporte, las comunas de cada rescatista (vacío = toda la ciudad) y la
tabla escalamientos (un aviso al coordinador por reporte).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reportes", sa.Column("comuna", sa.SmallInteger()))
    op.create_check_constraint("ck_reportes_comuna", "reportes", "comuna BETWEEN 1 AND 10")
    op.add_column("rescatistas", sa.Column("comunas", postgresql.ARRAY(sa.SmallInteger()),
                                           nullable=False, server_default=sa.text("'{}'")))
    op.create_check_constraint("ck_rescatistas_comunas", "rescatistas",
                               "comunas <@ ARRAY[1, 2, 3, 4, 5, 6, 7, 8, 9, 10]::smallint[]")
    op.create_table(
        "escalamientos",
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  primary_key=True),
        sa.Column("escalado_en", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("escalamientos")
    op.drop_column("rescatistas", "comunas")
    op.drop_column("reportes", "comuna")
