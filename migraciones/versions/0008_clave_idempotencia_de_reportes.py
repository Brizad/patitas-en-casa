"""Clave de idempotencia de los reportes (RF-12, #61).

Revisión: 0008
Anterior: 0007
Fecha: 2026-10-15

La PWA guarda el reporte sin señal y lo reenvía con la misma clave: la columna única impide
que el reenvío cree un segundo reporte. Los reportes anteriores quedan sin clave (NULL).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reportes", sa.Column("clave_idempotencia", sa.String(64)))
    op.create_unique_constraint("reportes_clave_idempotencia_key", "reportes",
                                ["clave_idempotencia"])


def downgrade() -> None:
    op.drop_constraint("reportes_clave_idempotencia_key", "reportes", type_="unique")
    op.drop_column("reportes", "clave_idempotencia")
