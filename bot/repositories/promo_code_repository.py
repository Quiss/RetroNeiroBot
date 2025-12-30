"""Репозиторий для работы с промокодами"""
import uuid
import random
import string
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.promo_code import PromoCode, PromoCodeUsage
from bot.models.user import User
from bot.logger import logger


class PromoCodeRepository:
    """Класс для работы с промокодами в БД"""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория

        Args:
            session: Сессия БД
        """
        self.session = session

    async def get_promo_code_by_code(self, code: str) -> Optional[PromoCode]:
        """
        Получить промокод по коду

        Args:
            code: Код промокода

        Returns:
            PromoCode или None, если промокод не найден
        """
        result = await self.session.execute(
            select(PromoCode).where(PromoCode.code == code.upper())
        )
        promo_code = result.scalar_one_or_none()

        if promo_code:
            logger.debug(f"Промокод найден: {code}")
        else:
            logger.debug(f"Промокод не найден: {code}")

        return promo_code

    async def check_user_used_promo_code(
        self, user_id: uuid.UUID, promo_code_id: uuid.UUID
    ) -> bool:
        """
        Проверить, использовал ли пользователь промокод

        Args:
            user_id: ID пользователя
            promo_code_id: ID промокода

        Returns:
            True, если пользователь уже использовал промокод
        """
        result = await self.session.execute(
            select(PromoCodeUsage).where(
                PromoCodeUsage.user_id == user_id,
                PromoCodeUsage.promo_code_id == promo_code_id,
            )
        )
        usage = result.scalar_one_or_none()
        return usage is not None

    async def activate_promo_code(
        self, user_telegram_id: int, code: str
    ) -> tuple[bool, str]:
        """
        Активировать промокод для пользователя

        Args:
            user_telegram_id: Telegram ID пользователя
            code: Код промокода

        Returns:
            Кортеж (успех, сообщение)
        """
        try:
            # Получаем пользователя
            user_result = await self.session.execute(
                select(User).where(User.telegram_id == user_telegram_id)
            )
            user = user_result.scalar_one_or_none()

            if not user:
                return False, "Пользователь не найден"

            # Получаем промокод
            promo_code = await self.get_promo_code_by_code(code)

            if not promo_code:
                logger.info(f"Попытка активации несуществующего промокода: {code}")
                return False, "invalid"

            # Проверяем, доступен ли промокод
            if not promo_code.is_available():
                logger.info(
                    f"Попытка активации исчерпанного промокода: {code} "
                    f"({promo_code.usage_count}/{promo_code.usage_limit})"
                )
                return False, "expired"

            # Проверяем, не использовал ли пользователь этот промокод ранее
            already_used = await self.check_user_used_promo_code(
                user.id, promo_code.id
            )

            if already_used:
                logger.info(
                    f"Пользователь {user_telegram_id} уже использовал промокод {code}"
                )
                return False, "already_used"

            # Начисляем генерации
            user.available_generation += promo_code.generation

            # Увеличиваем счетчик использований
            promo_code.usage_count += 1

            # Создаем запись об использовании
            usage = PromoCodeUsage(
                user_id=user.id,
                promo_code_id=promo_code.id,
            )
            self.session.add(usage)

            # Сохраняем изменения
            await self.session.commit()

            logger.info(
                f"Промокод {code} успешно активирован для пользователя {user_telegram_id}. "
                f"Начислено {promo_code.generation} генераций. "
                f"Использований: {promo_code.usage_count}/{promo_code.usage_limit}"
            )

            return True, str(promo_code.generation)

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка при активации промокода: {e}", exc_info=True)
            return False, "error"

    def _generate_promo_code(self, length: int = 8) -> str:
        """
        Сгенерировать случайный промокод

        Args:
            length: Длина промокода (по умолчанию 8)

        Returns:
            Строка с промокодом
        """
        # Используем только буквы и цифры, исключая похожие символы (0, O, I, 1)
        chars = string.ascii_uppercase.replace('O', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
        return ''.join(random.choice(chars) for _ in range(length))

    async def create_promo_code(
        self, generation: int, usage_limit: int
    ) -> Optional[str]:
        """
        Создать новый промокод

        Args:
            generation: Количество генераций
            usage_limit: Лимит использований

        Returns:
            Созданный промокод или None при ошибке
        """
        try:
            # Генерируем уникальный код
            max_attempts = 10
            code = None

            for _ in range(max_attempts):
                generated_code = self._generate_promo_code()
                # Проверяем, не существует ли уже такой код
                existing = await self.get_promo_code_by_code(generated_code)
                if not existing:
                    code = generated_code
                    break

            if not code:
                logger.error("Не удалось сгенерировать уникальный промокод")
                return None

            # Создаем промокод
            promo_code = PromoCode(
                code=code,
                generation=generation,
                usage_limit=usage_limit,
                usage_count=0,
            )

            self.session.add(promo_code)
            await self.session.commit()

            logger.info(
                f"Создан промокод: {code}, генераций: {generation}, лимит: {usage_limit}"
            )

            return code

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка при создании промокода: {e}", exc_info=True)
            return None
