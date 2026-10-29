"""Rol adoptante y su perfil (fase 3, #85, RF-08).

Revisión: 0016
Anterior: 0015
Fecha: 2026-10-29

Amplía el CHECK de roles y crea perfiles_adoptante (uno por cuenta). Bajar la revisión falla
si hay cuentas de adoptante: no se borran cuentas en silencio.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLES = "'veterinario', 'coordinador', 'rescatista', 'administrador'"


def upgrade() -> None:
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint("ck_usuarios_rol", "usuarios", f"rol IN ({ROLES}, 'adoptante')")
    op.create_table(
        "perfiles_adoptante",
        sa.Column("correo", sa.Text(), sa.ForeignKey("usuarios.correo"), primary_key=True),
        sa.Column("vivienda", sa.String(12), nullable=False),
        sa.Column("tiene_patio", sa.Boolean(), nullable=False),
        sa.Column("hay_ninos", sa.Boolean(), nullable=False),
        sa.Column("otros_animales", sa.Boolean(), nullable=False),
        sa.Column("horas_solo_al_dia", sa.SmallInteger(), nullable=False),
        sa.Column("experiencia", sa.Boolean(), nullable=False),
        sa.Column("acepta_seguimiento", sa.Boolean(), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("vivienda IN ('casa', 'apartamento', 'finca')",
                           name="ck_perfiles_vivienda"),
        sa.CheckConstraint("horas_solo_al_dia BETWEEN 0 AND 24", name="ck_perfiles_horas"),
    )


def downgrade() -> None:
    op.drop_table("perfiles_adoptante")
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint("ck_usuarios_rol", "usuarios", f"rol IN ({ROLES})")
