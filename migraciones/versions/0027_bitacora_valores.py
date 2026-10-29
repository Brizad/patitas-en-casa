"""Valor anterior y nuevo en la bitácora (RNF-12, #149).

Revisión: 0027
Anterior: 0026
Fecha: 2026-10-29

Dos columnas opcionales: los eventos viejos y las acciones sin un «antes» (crear un reporte)
quedan vacías. El disparador de la 0020 sigue rechazando UPDATE y DELETE; agregar columnas
no cambia filas.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("bitacora", sa.Column("valor_anterior", JSONB(), nullable=True))
    op.add_column("bitacora", sa.Column("valor_nuevo", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("bitacora", "valor_nuevo")
    op.drop_column("bitacora", "valor_anterior")
