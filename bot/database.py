"""Модуль для работы с базой данных"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.config import config
from bot.logger import logger


class Database:
    """Класс для управления подключением к базе данных"""

    def __init__(self, database_url: str):
        """
        Инициализация подключения к БД

        Args:
            database_url: URL подключения к PostgreSQL
        """
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            echo=False,  # Логирование SQL запросов
            pool_pre_ping=True,  # Проверка соединения перед использованием
            pool_size=10,  # Размер пула соединений
            max_overflow=20,  # Максимальное количество дополнительных соединений
        )

        self.session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

        logger.info("База данных инициализирована")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Контекстный менеджер для получения сессии БД

        Yields:
            AsyncSession: Сессия для работы с БД
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Ошибка при работе с БД: {e}")
                raise
            finally:
                await session.close()

    async def close(self):
        """Закрытие соединения с БД"""
        await self.engine.dispose()
        logger.info("Соединение с БД закрыто")


# Глобальный экземпляр Database
database = Database(config.database_url)


def get_db_session():
    """
    Helper функция для получения сессии БД в handlers

    Returns:
        Async context manager для сессии БД
    """
    return database.get_session()
