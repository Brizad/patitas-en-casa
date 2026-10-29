"""Reportes descartados por falsos o duplicados (fase 2, #75, D-02).

Revisión: 0013
Anterior: 0012
Fecha: 2026-10-29

Amplía el CHECK de estados con «descartado» y crea la bitácora de descartes (un descarte por
reporte: la llave primaria lo garantiza). Bajar la revisión falla si hay reportes
descartados: no se cambian estados en silencio.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ANTERIORES = "'recibido', 'clasificado', 'requiere_revision', 'sin_clasificar', 'confirmado'"


def upgrade() -> None:
    op.drop_constraint("ck_reportes_estado", "reportes", type_="check")
    op.create_check_constraint("ck_reportes_estado", "reportes",
                               f"estado IN ({ANTERIORES}, 'descartado')")
    op.create_table(
        "descartes",
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  primary_key=True),
        sa.Column("veterinario", sa.Text(), nullable=False),
        sa.Column("motivo", sa.String(10), nullable=False),
        sa.Column("duplicado_de", sa.String(8), sa.ForeignKey("reportes.codigo")),
        sa.Column("justificacion", sa.Text(), nullable=False),
        sa.Column("descartado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("motivo IN ('falso', 'duplicado')", name="ck_descartes_motivo"),
        sa.CheckConstraint("char_length(btrim(justificacion)) >= 10",
                           name="ck_descartes_justificacion"),
    )


def downgrade() -> None:
    op.drop_table("descartes")
    op.drop_constraint("ck_reportes_estado", "reportes", type_="check")
    op.create_check_constraint("ck_reportes_estado", "reportes", f"estado IN ({ANTERIORES})")
