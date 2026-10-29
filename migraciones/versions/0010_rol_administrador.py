"""Rol administrador (fase 1, #67, RF-14 y RF-16).

Revisión: 0010
Anterior: 0009
Fecha: 2026-10-28

Solo amplía el CHECK de roles: el código anterior nunca escribe «administrador».
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint(
        "ck_usuarios_rol", "usuarios",
        "rol IN ('veterinario', 'coordinador', 'rescatista', 'administrador')")


def downgrade() -> None:
    # Con cuentas de administrador el CHECK anterior falla y el downgrade se detiene: no se
    # borran cuentas en silencio.
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint("ck_usuarios_rol", "usuarios",
                               "rol IN ('veterinario', 'coordinador', 'rescatista')")
