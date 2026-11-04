"""Índices de los historiales del veterinario y del rescatista (DT-12, #265).

Revisión: 0034
Anterior: 0033
Fecha: 2026-11-05

`GET /veterinario/historial` filtra `decisiones_triaje` y `descartes` por veterinario y
`GET /rescates/historial` filtra `rescates` por rescatista; los índices únicos parciales de
`rescates` solo cubren los rescates activos.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

INDICES = (("ix_decisiones_triaje_veterinario", "decisiones_triaje",
            ["veterinario", "decidido_en"]),
           ("ix_descartes_veterinario", "descartes", ["veterinario", "descartado_en"]),
           ("ix_rescates_rescatista", "rescates", ["rescatista", "aceptado_en"]))


def upgrade() -> None:
    for nombre, tabla, columnas in INDICES:
        op.create_index(nombre, tabla, columnas)


def downgrade() -> None:
    for nombre, tabla, _ in reversed(INDICES):
        op.drop_index(nombre, table_name=tabla)
