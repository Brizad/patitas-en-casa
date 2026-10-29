"""Contacto opcional del ciudadano, cifrado (#111, RF-18, RNF-08).

Revisión: 0022
Anterior: 0021
Fecha: 2026-10-29

Columna opcional con el contacto cifrado (AES-256-GCM, base64). Los reportes existentes
quedan sin contacto.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("reportes", sa.Column("contacto_cifrado", sa.Text()))


def downgrade() -> None:
    op.drop_column("reportes", "contacto_cifrado")
