"""add credited to payments

Revision ID: 005
Revises: 004
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавление столбца credited в таблицу payments
    op.add_column(
        'payments',
        sa.Column('credited', sa.Boolean(), nullable=False, server_default='false', comment='Генерации зачислены')
    )


def downgrade() -> None:
    # Удаление столбца credited из таблицы payments
    op.drop_column('payments', 'credited')
