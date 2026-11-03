"""Hora de llegada del rescatista (#221).

Revisión: 0031
Anterior: 0030
Fecha: 2026-11-02

Columna opcional `rescates.llegada_en`: se llena cuando el rescatista pulsa «Llegué al sitio».
Los rescates anteriores quedan sin hora (NULL); no se inventa ninguna.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("rescates", sa.Column("llegada_en", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("rescates", "llegada_en")
