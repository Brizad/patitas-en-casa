"""#450: la publicación puede quedar «retirada» (el coordinador la saca del catálogo sin borrar).

Revisión: 0037
Anterior: 0036
Fecha: 2026-11-25

Migración aditiva: la restricción ck_publicaciones_estado solo AMPLÍA los valores permitidos
('disponible', 'adoptado') con 'retirada'. Ninguna fila cambia y todas las actuales siguen
cumpliendo. El downgrade vuelve a la restricción anterior (fallaría si ya hay retiradas).
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOMBRE = "ck_publicaciones_estado"


def upgrade() -> None:
    op.drop_constraint(NOMBRE, "publicaciones", type_="check")
    op.create_check_constraint(NOMBRE, "publicaciones",
                               "estado IN ('disponible', 'adoptado', 'retirada')")


def downgrade() -> None:
    op.drop_constraint(NOMBRE, "publicaciones", type_="check")
    op.create_check_constraint(NOMBRE, "publicaciones", "estado IN ('disponible', 'adoptado')")
