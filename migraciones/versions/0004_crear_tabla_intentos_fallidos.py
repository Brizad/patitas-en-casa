"""Crear la tabla intentos_fallidos (DT-06).

Revisión: 0004
Anterior: 0003
Fecha: 2026-10-15

Guarda los fallos de inicio de sesión por correo y por IP para limitar la fuerza bruta.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "intentos_fallidos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("clave", sa.Text(), nullable=False),
        sa.Column("ocurrido_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("clave <> ''", name="ck_intentos_fallidos_clave"),
    )
    op.create_index("ix_intentos_fallidos_clave_ocurrido_en", "intentos_fallidos",
                    ["clave", "ocurrido_en"])


def downgrade() -> None:
    op.drop_index("ix_intentos_fallidos_clave_ocurrido_en", table_name="intentos_fallidos")
    op.drop_table("intentos_fallidos")
