"""Adiciona coluna data_inicio_original na tabela contrato

Revision ID: 003
Revises: 002
Create Date: 2026-09-09 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Adiciona a coluna data_inicio_original se não existir
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'contrato' AND column_name = 'data_inicio_original'
            ) THEN
                ALTER TABLE contrato ADD COLUMN data_inicio_original DATE;
            END IF;
        END $$;
    """)

    # 2. Popula os registros existentes com a data_inicio atual
    op.execute("""
        UPDATE contrato
        SET data_inicio_original = data_inicio
        WHERE data_inicio_original IS NULL AND data_inicio IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'contrato' AND column_name = 'data_inicio_original'
            ) THEN
                ALTER TABLE contrato DROP COLUMN data_inicio_original;
            END IF;
        END $$;
    """)
