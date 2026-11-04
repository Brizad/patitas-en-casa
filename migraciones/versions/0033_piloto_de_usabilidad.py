"""Piloto de usabilidad (RNF-06, #258).

Revisión: 0033
Anterior: 0032
Fecha: 2026-11-05

Tabla `piloto`: un participante anónimo por fila, con el hash de su token de un solo uso, los
segundos hasta recibir el código y las 10 respuestas del SUS. El reporte de prueba no se guarda.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "piloto",
        sa.Column("codigo", sa.String(4), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vence_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reporte_en", sa.DateTime(timezone=True)),
        sa.Column("segundos", sa.Integer),
        sa.Column("sus", postgresql.ARRAY(sa.SmallInteger)),
        sa.Column("respondido_en", sa.DateTime(timezone=True)),
        sa.CheckConstraint("segundos BETWEEN 1 AND 3600", name="ck_piloto_segundos"),
        sa.CheckConstraint("sus IS NULL OR cardinality(sus) = 10", name="ck_piloto_sus"),
    )


def downgrade() -> None:
    op.drop_table("piloto")
