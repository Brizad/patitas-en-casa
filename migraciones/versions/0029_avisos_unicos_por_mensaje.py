"""Avisos distintos al mismo destinatario del mismo reporte.

Revisión: 0029
Anterior: 0028
Fecha: 2026-11-02

La unicidad de `avisos` pasa de (reporte, destinatario) a (reporte, destinatario, mensaje):
el ciudadano recibe un aviso al revisarse su reporte, otro al ser rescatado y otro al ingresar
al refugio. Repetir exactamente el mismo aviso sigue ignorándose. No cambia ningún dato.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_avisos_reporte_destinatario", "avisos", type_="unique")
    op.create_unique_constraint("uq_avisos_reporte_destinatario_mensaje", "avisos",
                                ["reporte_codigo", "destinatario", "mensaje"])


def downgrade() -> None:
    # Si ya hay varios avisos al mismo destinatario, se conserva el primero.
    op.execute("""DELETE FROM avisos a USING avisos b
                  WHERE a.reporte_codigo = b.reporte_codigo
                    AND a.destinatario = b.destinatario AND a.id > b.id""")
    op.drop_constraint("uq_avisos_reporte_destinatario_mensaje", "avisos", type_="unique")
    op.create_unique_constraint("uq_avisos_reporte_destinatario", "avisos",
                                ["reporte_codigo", "destinatario"])
