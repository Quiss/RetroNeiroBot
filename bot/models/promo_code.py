"""Модели для промокодов"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, DateTime, BigInteger, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.user import Base


class PromoCode(Base):
    """Модель промокода"""

    __tablename__ = "promo_codes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    generation: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Количество генераций, которые даёт промокод"
    )
    usage_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Максимальное количество активаций"
    )
    usage_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Текущее количество активаций"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    def is_available(self) -> bool:
        """Проверить, доступен ли промокод для активации"""
        return self.usage_count < self.usage_limit


class PromoCodeUsage(Base):
    """Модель использования промокода пользователем"""

    __tablename__ = "promo_code_usages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    promo_code_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("promo_codes.id", ondelete="CASCADE"),
        nullable=False,
    )
    used_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
