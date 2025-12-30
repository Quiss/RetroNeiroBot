"""Модель для платежей"""
import uuid
from datetime import datetime
from typing import Optional
from decimal import Decimal

from sqlalchemy import String, Integer, DateTime, BigInteger, Numeric, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class Payment(Base):
    """Модель платежа"""

    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    telegram_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="Telegram ID пользователя"
    )
    payment_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        comment="Статус платежа: pending, success, failed",
    )
    payment_driver: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Платежная система: robokassa"
    )
    sum: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, comment="Сумма платежа"
    )
    payment_link: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="Ссылка на оплату"
    )
    generations: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Количество генераций"
    )
    invoice_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="ID счета в платежной системе"
    )
    credited: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="Генерации зачислены"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
