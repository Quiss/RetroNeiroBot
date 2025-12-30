"""add generation check constraint

Revision ID: 007
Revises: 006
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем constraint: available_generation не может быть отрицательным
    op.create_check_constraint(
        'check_available_generation_not_negative',
        'users',
        'available_generation >= 0'
    )


def downgrade() -> None:
    # Удаляем constraint
    op.drop_constraint(
        'check_available_generation_not_negative',
        'users',
        type_='check'
    )
