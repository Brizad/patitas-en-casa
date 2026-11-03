"""Vista previa del video para el veterinario (#214, cambia RNF-08).

Revisión: 0030
Anterior: 0029
Fecha: 2026-11-02

Tabla nueva `vistas_trozos` (MP4 liviano por trozos de 1 MB) y tres columnas opcionales en
`analisis_video` que apuntan a ella. No toca datos existentes.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "vistas_trozos",
        sa.Column("ruta", sa.String(40), primary_key=True),
        sa.Column("orden", sa.Integer(), primary_key=True),
        sa.Column("datos", sa.LargeBinary(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("octet_length(datos) <= 1048576", name="ck_vistas_trozos_tamano"),
    )
    op.create_index("ix_vistas_trozos_creado", "vistas_trozos", ["creado_en"])
    op.add_column("analisis_video", sa.Column("vista_ruta", sa.String(40)))
    op.add_column("analisis_video", sa.Column("vista_bytes", sa.Integer()))
    op.add_column("analisis_video", sa.Column("vista_en", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("analisis_video", "vista_en")
    op.drop_column("analisis_video", "vista_bytes")
    op.drop_column("analisis_video", "vista_ruta")
    op.drop_index("ix_vistas_trozos_creado", table_name="vistas_trozos")
    op.drop_table("vistas_trozos")
