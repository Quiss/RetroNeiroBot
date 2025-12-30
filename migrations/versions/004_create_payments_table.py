"""create payments table

Revision ID: 004
Revises: 003
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание таблицы payments
    op.create_table(
        'payments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('telegram_id', sa.BigInteger(), nullable=False, comment='Telegram ID пользователя'),
        sa.Column('payment_status', sa.String(20), nullable=False, server_default='pending', comment='Статус платежа: pending, success, failed'),
        sa.Column('payment_driver', sa.String(50), nullable=False, comment='Платежная система: robokassa'),
        sa.Column('sum', sa.Numeric(10, 2), nullable=False, comment='Сумма платежа'),
        sa.Column('payment_link', sa.String(500), nullable=True, comment='Ссылка на оплату'),
        sa.Column('generations', sa.Integer(), nullable=False, comment='Количество генераций'),
        sa.Column('invoice_id', sa.String(100), nullable=True, comment='ID счета в платежной системе'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    # Создание индекса для telegram_id
    op.create_index('ix_payments_telegram_id', 'payments', ['telegram_id'])

    # Создание индекса для invoice_id
    op.create_index('ix_payments_invoice_id', 'payments', ['invoice_id'])


def downgrade() -> None:
    # Удаление индексов
    op.drop_index('ix_payments_invoice_id', table_name='payments')
    op.drop_index('ix_payments_telegram_id', table_name='payments')

    # Удаление таблицы
    op.drop_table('payments')
