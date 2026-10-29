"""Perfiles de adoptante cifrados (RNF-08, #149).

Revisión: 0026
Anterior: 0025
Fecha: 2026-10-29

Con PATITAS_CLAVE_DATOS, el perfil se guarda entero en `datos_cifrados` (AES-256-GCM) y las
columnas en claro quedan vacías. Por eso dejan de ser obligatorias. Los perfiles que ya
existían se cifran al arrancar la API (`cifrar_perfiles_en_claro`), porque la migración no
conoce la clave.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNAS = {"vivienda": sa.String(12), "tiene_patio": sa.Boolean(), "hay_ninos": sa.Boolean(),
            "otros_animales": sa.Boolean(), "horas_solo_al_dia": sa.SmallInteger(),
            "experiencia": sa.Boolean(), "acepta_seguimiento": sa.Boolean()}


def upgrade() -> None:
    op.add_column("perfiles_adoptante", sa.Column("datos_cifrados", sa.Text(), nullable=True))
    for nombre, tipo in COLUMNAS.items():
        op.alter_column("perfiles_adoptante", nombre, existing_type=tipo, nullable=True)
    # Cada perfil está en claro o cifrado, nunca a medias.
    op.create_check_constraint(
        "ck_perfiles_claro_o_cifrado", "perfiles_adoptante",
        "datos_cifrados IS NOT NULL OR (vivienda IS NOT NULL AND tiene_patio IS NOT NULL "
        "AND hay_ninos IS NOT NULL AND otros_animales IS NOT NULL "
        "AND horas_solo_al_dia IS NOT NULL AND experiencia IS NOT NULL "
        "AND acepta_seguimiento IS NOT NULL)")


def downgrade() -> None:
    # Los perfiles cifrados no se pueden pasar a claro sin la clave: se borran.
    op.execute("DELETE FROM perfiles_adoptante WHERE datos_cifrados IS NOT NULL")
    op.drop_constraint("ck_perfiles_claro_o_cifrado", "perfiles_adoptante")
    for nombre, tipo in COLUMNAS.items():
        op.alter_column("perfiles_adoptante", nombre, existing_type=tipo, nullable=False)
    op.drop_column("perfiles_adoptante", "datos_cifrados")
