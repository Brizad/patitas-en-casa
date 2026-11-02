"""Video temporal en PostgreSQL (#188, RF-03).

Revisión: 0028
Anterior: 0027
Fecha: 2026-11-02

Tabla nueva `videos_trozos`: el video espera por trozos de 1 MB hasta que el trabajador local
lo descarga. No toca ninguna tabla existente.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "videos_trozos",
        sa.Column("ruta", sa.String(40), primary_key=True),
        sa.Column("orden", sa.Integer(), primary_key=True),
        sa.Column("datos", sa.LargeBinary(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("octet_length(datos) <= 1048576", name="ck_videos_trozos_tamano"),
    )
    op.create_index("ix_videos_trozos_creado", "videos_trozos", ["creado_en"])


def downgrade() -> None:
    op.drop_index("ix_videos_trozos_creado", table_name="videos_trozos")
    op.drop_table("videos_trozos")
