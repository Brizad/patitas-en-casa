"""Avisos a rescatistas guardados antes de enviarse (outbox, #63).

Revisión: 0009
Anterior: 0008
Fecha: 2026-10-22

Solo agrega una tabla (cambio compatible): la versión anterior del código no la lee ni la
escribe. No se migran datos: los avisos de reportes confirmados antes de esta revisión ya se
intentaron enviar con el camino anterior. Bajar la revisión borra los avisos pendientes.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "avisos",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  nullable=False),
        sa.Column("destinatario", sa.Text(), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False),
        sa.Column("intentos", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("ultimo_error", sa.Text()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("proximo_intento_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reclamado_en", sa.DateTime(timezone=True)),
        sa.Column("enviado_en", sa.DateTime(timezone=True)),
        sa.CheckConstraint("estado IN ('pendiente', 'enviando', 'enviado', 'fallido')",
                           name="ck_avisos_estado"),
        sa.CheckConstraint("intentos >= 0", name="ck_avisos_intentos"),
        sa.UniqueConstraint("reporte_codigo", "destinatario",
                            name="uq_avisos_reporte_destinatario"),
    )
    op.create_index("ix_avisos_estado_proximo_intento", "avisos",
                    ["estado", "proximo_intento_en"])


def downgrade() -> None:
    op.drop_index("ix_avisos_estado_proximo_intento", table_name="avisos")
    op.drop_table("avisos")
