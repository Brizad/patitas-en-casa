"""Perfil de adopción del animal: habilidades y salud (#508).

Revisión: 0041
Anterior: 0040
Fecha: 2026-11-28

Aditiva: columnas nuevas en publicaciones, todas opcionales (NULL), sin tocar las que existen.
Las estadísticas 1 a 5 no necesitan columnas: salen de carino, energia_nivel, juego y calma (0036).

- habilidades: hasta 8, de un catálogo fijo (app/adopciones/perfil.py; lo valida la API).
- vacunas, esterilizado, desparasitado: sí, no o NULL (sin dato). Las edita solo el veterinario.
  No se reutilizan animales.vacunado/esterilizado: son casillas del ingreso, NOT NULL con falso
  por defecto, y no distinguen «no» de «sin dato».
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SALUD = ("vacunas", "esterilizado", "desparasitado")


def upgrade() -> None:
    op.add_column("publicaciones", sa.Column("habilidades", ARRAY(sa.String(30)), nullable=True))
    op.create_check_constraint("ck_publicaciones_habilidades", "publicaciones",
                               "cardinality(habilidades) <= 8")
    for campo in SALUD:
        op.add_column("publicaciones", sa.Column(campo, sa.Boolean(), nullable=True))


def downgrade() -> None:
    for nombre in (*SALUD, "habilidades"):
        op.drop_column("publicaciones", nombre)  # se lleva su CHECK
