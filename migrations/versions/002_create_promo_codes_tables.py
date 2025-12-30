"""create promo_codes and promo_code_usages tables

Revision ID: 002
Revises: 001
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание таблицы promo_codes
    op.create_table(
        'promo_codes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(50), nullable=False),
        sa.Column('generation', sa.Integer(), nullable=False, comment='Количество генераций, которые даёт промокод'),
        sa.Column('usage_limit', sa.Integer(), nullable=False, comment='Максимальное количество активаций'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0', comment='Текущее количество активаций'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Создание уникального индекса для code
    op.create_index('ix_promo_codes_code', 'promo_codes', ['code'], unique=True)

    # Создание таблицы promo_code_usages
    op.create_table(
        'promo_code_usages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('promo_code_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['promo_code_id'], ['promo_codes.id'], ondelete='CASCADE'),
    )

    # Создание индексов для быстрого поиска
    op.create_index('ix_promo_code_usages_user_id', 'promo_code_usages', ['user_id'])
    op.create_index('ix_promo_code_usages_promo_code_id', 'promo_code_usages', ['promo_code_id'])


def downgrade() -> None:
    # Удаление индексов promo_code_usages
    op.drop_index('ix_promo_code_usages_promo_code_id', table_name='promo_code_usages')
    op.drop_index('ix_promo_code_usages_user_id', table_name='promo_code_usages')

    # Удаление таблицы promo_code_usages
    op.drop_table('promo_code_usages')

    # Удаление индекса promo_codes
    op.drop_index('ix_promo_codes_code', table_name='promo_codes')

    # Удаление таблицы promo_codes
    op.drop_table('promo_codes')
