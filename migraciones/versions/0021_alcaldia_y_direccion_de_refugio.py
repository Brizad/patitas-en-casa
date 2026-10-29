"""Rol Alcaldía y dirección del refugio (#108, RF-13 y RF-14 del ERS).

Revisión: 0021
Anterior: 0020
Fecha: 2026-10-29

Amplía el CHECK de roles con «alcaldia» (consulta indicadores anonimizados) y agrega la
dirección opcional del refugio (los refugios existentes quedan sin dirección).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = "'veterinario', 'coordinador', 'rescatista', 'administrador', 'adoptante'"


def upgrade() -> None:
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint("ck_usuarios_rol", "usuarios", f"rol IN ({ROLES}, 'alcaldia')")
    op.add_column("refugios", sa.Column("direccion", sa.Text()))


def downgrade() -> None:
    op.drop_column("refugios", "direccion")
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint("ck_usuarios_rol", "usuarios", f"rol IN ({ROLES})")
