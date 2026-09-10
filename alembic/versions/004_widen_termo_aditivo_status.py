"""Altera tamanho da coluna status em termo_aditivo para VARCHAR(50)

Revision ID: 004
Revises: 003
Create Date: 2026-09-10 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'termo_aditivo' AND column_name = 'status'
            ) THEN
                ALTER TABLE termo_aditivo ALTER COLUMN status TYPE VARCHAR(50);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'termo_aditivo' AND column_name = 'status'
            ) THEN
                ALTER TABLE termo_aditivo ALTER COLUMN status TYPE VARCHAR(20);
            END IF;
        END $$;
    """)
