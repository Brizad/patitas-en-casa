"""Personal vinculado a un refugio (fase 1, #67, RF-14).

Revisión: 0011
Anterior: 0010
Fecha: 2026-10-28

Columna opcional: las cuentas existentes quedan sin refugio (NULL) y el código anterior no la
lee. Bajar la revisión pierde los vínculos, no las cuentas.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("usuarios", sa.Column("refugio_id", sa.Integer(),
                                        sa.ForeignKey("refugios.id"), nullable=True))


def downgrade() -> None:
    op.drop_column("usuarios", "refugio_id")
