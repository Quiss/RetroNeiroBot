"""Репозиторий для работы с платежами"""
import uuid
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.payment import Payment
from bot.logger import logger


class PaymentRepository:
    """Класс для работы с платежами в БД"""

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория

        Args:
            session: Сессия БД
        """
        self.session = session

    async def create_payment(
        self,
        telegram_id: int,
        payment_driver: str,
        sum: Decimal,
        generations: int,
        payment_link: Optional[str] = None,
        invoice_id: Optional[str] = None,
    ) -> Payment:
        """
        Создать новый платеж

        Args:
            telegram_id: Telegram ID пользователя
            payment_driver: Платежная система
            sum: Сумма платежа
            generations: Количество генераций
            payment_link: Ссылка на оплату
            invoice_id: ID счета

        Returns:
            Созданный платеж
        """
        payment = Payment(
            telegram_id=telegram_id,
            payment_driver=payment_driver,
            sum=sum,
            generations=generations,
            payment_link=payment_link,
            invoice_id=invoice_id,
            payment_status="pending",
        )

        self.session.add(payment)
        await self.session.commit()
        await self.session.refresh(payment)

        logger.info(
            f"Создан платеж {payment.id} для пользователя {telegram_id}: "
            f"{sum} руб за {generations} генераций"
        )

        return payment

    async def get_payment_by_id(self, payment_id: uuid.UUID) -> Optional[Payment]:
        """
        Получить платеж по ID

        Args:
            payment_id: ID платежа

        Returns:
            Payment или None
        """
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_payment_by_invoice_id(self, invoice_id: str) -> Optional[Payment]:
        """
        Получить платеж по invoice_id

        Args:
            invoice_id: ID счета

        Returns:
            Payment или None
        """
        result = await self.session.execute(
            select(Payment).where(Payment.invoice_id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def update_payment_status(
        self, payment_id: uuid.UUID, status: str
    ) -> bool:
        """
        Обновить статус платежа

        Args:
            payment_id: ID платежа
            status: Новый статус (pending, success, failed)

        Returns:
            True если обновление успешно
        """
        try:
            result = await self.session.execute(
                update(Payment)
                .where(Payment.id == payment_id)
                .values(payment_status=status)
            )
            await self.session.commit()

            if result.rowcount > 0:
                logger.info(f"Статус платежа {payment_id} обновлен на '{status}'")
                return True
            else:
                logger.warning(f"Платеж {payment_id} не найден")
                return False

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка при обновлении статуса платежа: {e}", exc_info=True)
            return False

    async def get_pending_payment_by_telegram_id(
        self, telegram_id: int
    ) -> Optional[Payment]:
        """
        Получить ожидающий платеж пользователя

        Args:
            telegram_id: Telegram ID пользователя

        Returns:
            Payment или None
        """
        result = await self.session.execute(
            select(Payment)
            .where(Payment.telegram_id == telegram_id)
            .where(Payment.payment_status == "pending")
            .order_by(Payment.created_at.desc())
        )
        return result.scalar_one_or_none()

    async def mark_as_credited(self, payment_id: uuid.UUID) -> bool:
        """
        Отметить платеж как зачисленный

        Args:
            payment_id: ID платежа

        Returns:
            True если обновление успешно
        """
        try:
            result = await self.session.execute(
                update(Payment)
                .where(Payment.id == payment_id)
                .values(credited=True)
            )
            await self.session.commit()

            if result.rowcount > 0:
                logger.info(f"Платеж {payment_id} отмечен как зачисленный")
                return True
            else:
                logger.warning(f"Платеж {payment_id} не найден")
                return False

        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка при обновлении платежа: {e}", exc_info=True)
            return False
