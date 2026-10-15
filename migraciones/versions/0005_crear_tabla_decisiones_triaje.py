"""Crear la bitácora de decisiones de triaje (HU-02).

Revisión: 0005
Anterior: 0004
Fecha: 2026-10-15

Una fila por reporte confirmado: quién decidió, la prioridad sugerida, la final y la
justificación, que es obligatoria si la prioridad cambió (RN-16).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PRIORIDADES = "('critica', 'alta', 'media', 'baja')"


def upgrade() -> None:
    op.create_table(
        "decisiones_triaje",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  nullable=False),
        sa.Column("veterinario", sa.Text(), nullable=False),
        sa.Column("prioridad_sugerida", sa.String(10), nullable=False),
        sa.Column("prioridad_final", sa.String(10), nullable=False),
        sa.Column("justificacion", sa.Text()),
        sa.Column("decidido_en", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.CheckConstraint(f"prioridad_sugerida IN {PRIORIDADES}",
                           name="ck_decisiones_prioridad_sugerida"),
        sa.CheckConstraint(f"prioridad_final IN {PRIORIDADES}",
                           name="ck_decisiones_prioridad_final"),
        # El IS NOT NULL importa: un CHECK que da NULL deja pasar la fila.
        sa.CheckConstraint("prioridad_final = prioridad_sugerida OR (justificacion IS NOT NULL "
                           "AND char_length(btrim(justificacion)) >= 10)",
                           name="ck_decisiones_justificacion"),
        sa.UniqueConstraint("reporte_codigo", name="uq_decisiones_reporte"),
    )


def downgrade() -> None:
    op.drop_table("decisiones_triaje")
