"""RN-01 también en la base: la descripción del reporte tiene 20 caracteres o más.

Revisión: 0035
Anterior: 0034
Fecha: 2026-11-17

Hasta hoy la regla vivía solo en `ServicioReportes.validar`: un INSERT directo podía saltársela.

Migración aditiva y sin riesgo para los datos que ya existen:

1. La restricción se crea `NOT VALID`: PostgreSQL la exige a las filas nuevas y a las que se
   modifiquen, pero no revisa (ni bloquea) las que ya están.
2. Solo si **todas** las filas actuales cumplen, se valida (`VALIDATE CONSTRAINT`). Si alguna
   no cumple, no se toca ninguna fila: la restricción queda sin validar y se avisa en el log.

Ojo con el caso 2: modificar una de esas filas viejas (confirmarla, descartarla) fallaría hasta
corregir su descripción. Para verlas: SELECT codigo FROM reportes WHERE
char_length(btrim(descripcion, E' \\t\\n\\r')) < 20;
"""
import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOMBRE = "ck_reportes_descripcion"
CONDICION = "char_length(btrim(descripcion, E' \\t\\n\\r')) >= 20"
log = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    op.execute(f"ALTER TABLE reportes ADD CONSTRAINT {NOMBRE} CHECK ({CONDICION}) NOT VALID")
    cortas = op.get_bind().execute(
        text(f"SELECT count(*) FROM reportes WHERE NOT ({CONDICION})")).scalar_one()
    if cortas == 0:
        op.execute(f"ALTER TABLE reportes VALIDATE CONSTRAINT {NOMBRE}")
    else:
        log.warning("RN-01: %d reportes anteriores tienen una descripción de menos de 20 "
                    "caracteres; %s queda sin validar (vale para los nuevos).", cortas, NOMBRE)


def downgrade() -> None:
    op.drop_constraint(NOMBRE, "reportes", type_="check")
