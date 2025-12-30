"""add is_admin column to users table

Revision ID: 003
Revises: 002
Create Date: 2025-12-29

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
    # Добавление колонки is_admin в таблицу users
    op.add_column(
        'users',
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false')
    )


def downgrade() -> None:
    # Удаление колонки is_admin из таблицы users
    op.drop_column('users', 'is_admin')
