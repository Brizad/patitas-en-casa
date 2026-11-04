"""Índices de la cola y de los duplicados (auditoría A-03, #239).

Revisión: 0032
Anterior: 0031
Fecha: 2026-11-04

`GET /cola` filtra los reportes por estado y la detección de duplicados (RF-17) por fecha de
creación. Sin estos índices PostgreSQL recorre toda la tabla en cada consulta.
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("ix_reportes_estado", "reportes", ["estado"])
    op.create_index("ix_reportes_creado_en", "reportes", ["creado_en"])


def downgrade() -> None:
    op.drop_index("ix_reportes_creado_en", table_name="reportes")
    op.drop_index("ix_reportes_estado", table_name="reportes")
