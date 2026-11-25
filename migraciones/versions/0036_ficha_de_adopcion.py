"""Ficha «Elige a tu compañero» en la publicación de adopción (#422).

Revisión: 0036
Anterior: 0035
Fecha: 2026-11-25

Aditiva: columnas nuevas, todas opcionales (NULL), sin tocar las que ya existen. `energia`
(baja/media/alta) se queda: la usa la compatibilidad (RF-09). Las nuevas son solo para mostrar:

- carino, energia_nivel, juego, calma: de 0 a 100.
- etiquetas: hasta 3 textos cortos (20 caracteres).
- peso_kg (hoy) y peso_adulto_kg (estimado), mayores que 0 y hasta 150 kg.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NIVELES = ("carino", "energia_nivel", "juego", "calma")


def upgrade() -> None:
    for nivel in NIVELES:
        op.add_column("publicaciones", sa.Column(nivel, sa.SmallInteger(), nullable=True))
        op.create_check_constraint(f"ck_publicaciones_{nivel}", "publicaciones",
                                   f"{nivel} BETWEEN 0 AND 100")
    op.add_column("publicaciones", sa.Column("etiquetas", ARRAY(sa.String(20)), nullable=True))
    op.create_check_constraint("ck_publicaciones_etiquetas", "publicaciones",
                               "cardinality(etiquetas) <= 3")
    for peso in ("peso_kg", "peso_adulto_kg"):
        op.add_column("publicaciones", sa.Column(peso, sa.Numeric(5, 2), nullable=True))
    op.create_check_constraint("ck_publicaciones_peso", "publicaciones",
                               "peso_kg > 0 AND peso_kg <= 150")
    op.create_check_constraint("ck_publicaciones_peso_adulto", "publicaciones",
                               "peso_adulto_kg > 0 AND peso_adulto_kg <= 150")


def downgrade() -> None:
    for nombre in ("peso_adulto_kg", "peso_kg", "etiquetas", *NIVELES):
        op.drop_column("publicaciones", nombre)  # se lleva su CHECK
