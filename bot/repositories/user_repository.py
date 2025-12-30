"""Репозиторий для работы с пользователями"""
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user import User
from bot.logger import logger


class UserRepository:
    """Класс для работы с пользователями в БД"""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория

        Args:
            session: Сессия БД
        """
        self.session = session

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """
        Получить пользователя по Telegram ID

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            User или None, если пользователь не найден
        """
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user:
            logger.debug(f"Пользователь найден: {telegram_id}")
        else:
            logger.debug(f"Пользователь не найден: {telegram_id}")

        return user

    async def create_user(
        self,
        telegram_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        referral_telegram_id: Optional[int] = None,
        initial_generations: int = 0,
    ) -> User:
        """
        Создать нового пользователя

        Args:
            telegram_id: Telegram ID
            first_name: Имя
            last_name: Фамилия (опционально)
            username: Username (опционально)
            referral_telegram_id: ID пригласившего (опционально)
            initial_generations: Начальное количество генераций

        Returns:
            Созданный пользователь
        """
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            referral_telegram_id=referral_telegram_id,
            available_generation=initial_generations,
        )

        self.session.add(user)
        await self.session.flush()

        logger.info(
            f"Создан пользователь: {telegram_id} (@{username}), "
            f"реферал: {referral_telegram_id}"
        )

        return user

    async def update_generations(self, telegram_id: int, delta: int) -> bool:
        """
        Обновить количество доступных генераций

        Args:
            telegram_id: Telegram ID пользователя
            delta: Изменение количества генераций (может быть отрицательным)

        Returns:
            True, если обновление прошло успешно
        """
        result = await self.session.execute(
            update(User)
            .where(User.telegram_id == telegram_id)
            .values(available_generation=User.available_generation + delta)
        )

        if result.rowcount > 0:
            logger.info(
                f"Обновлены генерации для {telegram_id}: "
                f"{'+'if delta >= 0 else ''}{delta}"
            )
            return True

        logger.warning(f"Не удалось обновить генерации для {telegram_id}")
        return False

    async def add_referral_bonus(
        self, referrer_telegram_id: int, bonus_generations: int
    ) -> bool:
        """
        Начислить бонус за реферала

        Args:
            referrer_telegram_id: Telegram ID пригласившего пользователя
            bonus_generations: Количество бонусных генераций

        Returns:
            True, если начисление прошло успешно
        """
        result = await self.session.execute(
            update(User)
            .where(User.telegram_id == referrer_telegram_id)
            .values(
                available_generation=User.available_generation + bonus_generations,
                referral_generation=User.referral_generation + bonus_generations,
            )
        )

        if result.rowcount > 0:
            logger.info(
                f"Начислен реферальный бонус {referrer_telegram_id}: "
                f"+{bonus_generations} генераций"
            )
            return True

        logger.warning(
            f"Не удалось начислить реферальный бонус для {referrer_telegram_id}"
        )
        return False

    async def get_user_balance(self, telegram_id: int) -> Optional[int]:
        """
        Получить баланс генераций пользователя

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Количество доступных генераций или None
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        return user.available_generation if user else None

    async def get_referral_stats(self, telegram_id: int) -> Optional[int]:
        """
        Получить статистику рефералов

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Количество генераций, полученных от рефералов, или None
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        return user.referral_generation if user else None

    async def has_referred_by(self, telegram_id: int) -> bool:
        """
        Проверить, был ли пользователь приглашен кем-то

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            True, если пользователь был приглашен
        """
        user = await self.get_user_by_telegram_id(telegram_id)
        return user.referral_telegram_id is not None if user else False

    async def try_spend_generation(self, telegram_id: int) -> tuple[bool, Optional[int]]:
        """
        Атомарно проверить баланс и списать одну генерацию

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Кортеж (успешно_ли_списано, новый_баланс_или_текущий)
            - (True, new_balance) - успешно списано
            - (False, current_balance) - недостаточно генераций (0 или больше)
            - (False, None) - пользователь не найден
        """
        # Используем SELECT FOR UPDATE для блокировки строки
        # Это предотвращает race condition при параллельных запросах
        result = await self.session.execute(
            select(User)
            .where(User.telegram_id == telegram_id)
            .with_for_update()  # Блокируем строку для обновления
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(f"Пользователь не найден: {telegram_id}")
            return False, None

        # Проверяем баланс
        if user.available_generation <= 0:
            logger.info(f"Недостаточно генераций у {telegram_id}: {user.available_generation}")
            return False, user.available_generation

        # Списываем генерацию
        user.available_generation -= 1
        await self.session.commit()

        logger.info(f"Списана генерация у {telegram_id}: новый баланс {user.available_generation}")
        return True, user.available_generation
