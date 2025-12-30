"""increase payment_link length

Revision ID: 006
Revises: 005
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Увеличиваем размер поля payment_link с 500 до 1000 символов
    op.alter_column(
        'payments',
        'payment_link',
        type_=sa.String(1000),
        existing_type=sa.String(500),
        existing_nullable=True,
        existing_comment='Ссылка на оплату'
    )


def downgrade() -> None:
    # Возвращаем обратно к 500 символам
    op.alter_column(
        'payments',
        'payment_link',
        type_=sa.String(500),
        existing_type=sa.String(1000),
        existing_nullable=True,
        existing_comment='Ссылка на оплату'
    )
