"""Crear la tabla usuarios (DT-02).

Revisión: 0003
Anterior: 0002
Fecha: 2026-10-15

No se crea ningún usuario: las cuentas se crean con python -m app.usuarios.crear_usuario.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("correo", sa.Text(), nullable=False),
        sa.Column("nombre", sa.Text(), nullable=False),
        sa.Column("rol", sa.String(20), nullable=False),
        sa.Column("hash_contrasena", sa.Text(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.UniqueConstraint("correo", name="uq_usuarios_correo"),
        sa.CheckConstraint("correo = lower(correo)", name="ck_usuarios_correo_minusculas"),
        sa.CheckConstraint("rol IN ('veterinario', 'coordinador')", name="ck_usuarios_rol"),
    )


def downgrade() -> None:
    op.drop_table("usuarios")
