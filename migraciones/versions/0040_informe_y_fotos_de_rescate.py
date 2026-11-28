"""#504: informe del rescatista en el sitio y fotos de evidencia.

Revisión: 0040
Anterior: 0039
Fecha: 2026-11-28

Migración aditiva:
- crea informes_rescate (uno por reporte) y fotos_evidencia (bytea; del rescate o del reporte
  del ciudadano), sin tocar ninguna tabla existente;
- ck_rescates_resultado solo AMPLÍA los valores con 'veterinaria' y 'no_rescatado'. Ninguna
  fila cambia y todas las actuales siguen cumpliendo.
El downgrade borra solo las tablas nuevas y vuelve a la restricción anterior (fallaría si ya hay
rescates con los resultados nuevos).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ANTERIORES = "'trasladado', 'atendido_en_sitio', 'no_encontrado', 'fallecido'"


def upgrade() -> None:
    op.drop_constraint("ck_rescates_resultado", "rescates", type_="check")
    op.create_check_constraint("ck_rescates_resultado", "rescates",
                               f"resultado IN ({ANTERIORES}, 'veterinaria', 'no_rescatado')")
    op.create_table(
        "informes_rescate",
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  primary_key=True),
        sa.Column("rescatista", sa.Text(), nullable=False),
        sa.Column("encontrado", sa.String(12), nullable=False),
        sa.Column("estados", ARRAY(sa.String(20)), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("resultado", sa.String(20), nullable=False),
        sa.Column("motivo", sa.Text()),
        sa.Column("nota", sa.Text()),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("encontrado IN ('si', 'no_estaba', 'otro_animal')",
                           name="ck_informes_encontrado"),
        sa.CheckConstraint("nota IS NULL OR char_length(nota) <= 500", name="ck_informes_nota"),
    )
    op.create_table(
        "fotos_evidencia",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("reporte_codigo", sa.String(8), sa.ForeignKey("reportes.codigo"),
                  nullable=False),
        sa.Column("origen", sa.String(8), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("datos", sa.LargeBinary(), nullable=False),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("origen IN ('reporte', 'rescate')", name="ck_fotos_evidencia_origen"),
        sa.CheckConstraint("octet_length(datos) <= 1048576", name="ck_fotos_evidencia_tamano"),
    )
    op.create_index("ix_fotos_evidencia_reporte", "fotos_evidencia", ["reporte_codigo"])
    op.create_index("uq_fotos_evidencia_reporte", "fotos_evidencia", ["reporte_codigo"],
                    unique=True, postgresql_where=sa.text("origen = 'reporte'"))


def downgrade() -> None:
    op.drop_table("fotos_evidencia")
    op.drop_table("informes_rescate")
    op.drop_constraint("ck_rescates_resultado", "rescates", type_="check")
    op.create_check_constraint("ck_rescates_resultado", "rescates",
                               f"resultado IN ({ANTERIORES})")
