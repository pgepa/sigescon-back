"""Baseline do schema do SIGESCON

Revision ID: 001
Revises: 
Create Date: 2026-09-08 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Baseline representa a estrutura existente do banco de dados (tabelas principais criadas previamente)
    pass


def downgrade() -> None:
    pass
