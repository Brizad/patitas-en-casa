"""Rescatistas y rescates (HU-06, RN-08).

Revisión: 0006
Anterior: 0005
Fecha: 2026-10-15

Agrega el rol rescatista, su disponibilidad y la tabla de rescates. RN-08 queda en dos índices
únicos parciales: un rescate vigente por reporte y un rescate activo por rescatista.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint("ck_usuarios_rol", "usuarios",
                               "rol IN ('veterinario', 'coordinador', 'rescatista')")
    op.create_table(
        "rescatistas",
        sa.Column("correo", sa.Text(), primary_key=True),
        sa.Column("disponible", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_table(
        "rescates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  nullable=False),
        sa.Column("rescatista", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(12), nullable=False),
        sa.Column("resultado", sa.String(20)),
        sa.Column("aceptado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("estado IN ('en_camino', 'en_sitio', 'atendido', 'liberado')",
                           name="ck_rescates_estado"),
        sa.CheckConstraint("resultado IN ('trasladado', 'atendido_en_sitio', 'no_encontrado', "
                           "'fallecido')", name="ck_rescates_resultado"),
        sa.CheckConstraint("(estado = 'atendido') = (resultado IS NOT NULL)",
                           name="ck_rescates_resultado_al_atender"),
    )
    op.create_index("uq_rescates_reporte_vigente", "rescates", ["reporte_codigo"], unique=True,
                    postgresql_where=sa.text("estado <> 'liberado'"))
    op.create_index("uq_rescates_rescatista_activo", "rescates", ["rescatista"], unique=True,
                    postgresql_where=sa.text("estado IN ('en_camino', 'en_sitio')"))


def downgrade() -> None:
    op.drop_index("uq_rescates_rescatista_activo", table_name="rescates")
    op.drop_index("uq_rescates_reporte_vigente", table_name="rescates")
    op.drop_table("rescates")
    op.drop_table("rescatistas")
    # Si quedan cuentas de rescatista, el CHECK anterior falla y el downgrade se detiene:
    # no se borran cuentas en silencio.
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.create_check_constraint("ck_usuarios_rol", "usuarios",
                               "rol IN ('veterinario', 'coordinador')")
