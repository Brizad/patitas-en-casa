"""Bitácora general inmutable (fase 5, #102, RF-32, RNF-12).

Revisión: 0020
Anterior: 0019
Fecha: 2026-10-29

Crea la tabla y un disparador que rechaza UPDATE y DELETE: la historia solo crece. (TRUNCATE
no dispara triggers de fila; solo lo usan las pruebas sobre la base de pruebas.)
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bitacora",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("momento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("accion", sa.Text(), nullable=False),
        sa.Column("objeto", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("estado_http", sa.SmallInteger(), nullable=False),
    )
    op.execute("""
        CREATE FUNCTION bitacora_inmutable() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'La bitácora es inmutable: no se puede % (RF-32)', TG_OP;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("CREATE TRIGGER tr_bitacora_inmutable BEFORE UPDATE OR DELETE ON bitacora "
               "FOR EACH ROW EXECUTE FUNCTION bitacora_inmutable()")


def downgrade() -> None:
    op.execute("DROP TRIGGER tr_bitacora_inmutable ON bitacora")
    op.execute("DROP FUNCTION bitacora_inmutable()")
    op.drop_table("bitacora")
