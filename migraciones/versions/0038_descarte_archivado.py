"""#496: el veterinario archiva un caso atrasado que no se pudo verificar (motivo «archivado»).

Revisión: 0038
Anterior: 0037
Fecha: 2026-11-27

Migración aditiva: ck_descartes_motivo solo AMPLÍA los valores permitidos ('falso', 'duplicado')
con 'archivado'. Ninguna fila cambia y todas las actuales siguen cumpliendo. El archivo queda en
la tabla descartes (quién, cuándo y por qué), como cualquier descarte. El downgrade vuelve a la
restricción anterior (fallaría si ya hay archivados).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOMBRE = "ck_descartes_motivo"


def upgrade() -> None:
    op.drop_constraint(NOMBRE, "descartes", type_="check")
    op.create_check_constraint(NOMBRE, "descartes", "motivo IN ('falso', 'duplicado', 'archivado')")


def downgrade() -> None:
    op.drop_constraint(NOMBRE, "descartes", type_="check")
    op.create_check_constraint(NOMBRE, "descartes", "motivo IN ('falso', 'duplicado')")
