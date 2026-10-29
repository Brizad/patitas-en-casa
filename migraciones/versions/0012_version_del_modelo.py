"""Versión del modelo en reportes y decisiones (fase 2, #75, RF-20, D-04).

Revisión: 0012
Anterior: 0011
Fecha: 2026-10-29

Dos columnas opcionales. Las filas anteriores quedan en NULL: no se inventa una versión que
no se registró.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reportes", sa.Column("version_modelo", sa.String(40)))
    op.add_column("decisiones_triaje", sa.Column("version_modelo", sa.String(40)))


def downgrade() -> None:
    op.drop_column("decisiones_triaje", "version_modelo")
    op.drop_column("reportes", "version_modelo")
