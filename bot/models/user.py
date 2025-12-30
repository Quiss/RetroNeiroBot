from datetime import datetime
from typing import Optional
import uuid

from sqlalchemy import BigInteger, Integer, Text, TIMESTAMP, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Базовый класс для всех моделей"""
    pass


class User(Base):
    """Модель пользователя бота"""
    __tablename__ = "users"

    # Внутренний ID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Telegram ID пользователя (уникальный)
    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        unique=True,
        nullable=False,
        index=True
    )

    # Имя пользователя
    first_name: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # Фамилия пользователя (опционально)
    last_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Username пользователя (опционально)
    username: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Доступное количество генераций
    available_generation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Telegram ID пригласившего пользователя (опционально)
    referral_telegram_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        nullable=True
    )

    # Всего генераций получено от рефералов
    referral_generation: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )

    # Дата регистрации
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        default=datetime.utcnow
    )

    # Является ли пользователь администратором
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"
