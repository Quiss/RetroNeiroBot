"""Главный файл для запуска бота"""
import asyncio
import sys
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

from bot.config import config
from bot.logger import logger
from bot.database import database, get_db_session
from bot.repositories.payment_repository import PaymentRepository
from bot.repositories.user_repository import UserRepository
from bot.services.robokassa import robokassa_service

# Импорт роутеров
from bot.handlers import start, menu, image_processing, promo_code, admin_promo_code


async def check_pending_payments(bot: Bot):
    """
    Фоновая задача для автоматической проверки платежей
    Запускается каждую минуту и проверяет все pending платежи
    """
    while True:
        try:
            await asyncio.sleep(40)  # Проверяем каждую минуту

            async with get_db_session() as session:
                payment_repo = PaymentRepository(session)
                user_repo = UserRepository(session)

                # Получаем все платежи со статусом pending
                from sqlalchemy import select
                from bot.models.payment import Payment

                result = await session.execute(
                    select(Payment).where(Payment.payment_status == "pending")
                )
                pending_payments = result.scalars().all()

                logger.info(f"Проверка {len(pending_payments)} ожидающих платежей")

                for payment in pending_payments:
                    try:
                        # Проверяем возраст платежа
                        payment_age = datetime.utcnow() - payment.created_at

                        # Если платеж старше 1 часа, помечаем как failed
                        if payment_age > timedelta(hours=1):
                            await payment_repo.update_payment_status(payment.id, "failed")
                            logger.info(
                                f"Платеж {payment.id} помечен как failed (прошло {payment_age})"
                            )
                            continue

                        # Проверяем только если есть invoice_id
                        if not payment.invoice_id or not payment.invoice_id.isdigit():
                            continue

                        # Проверяем статус через API Robokassa
                        robokassa_status = await robokassa_service.check_payment_status(
                            payment.invoice_id
                        )

                        if robokassa_status == "success" and not payment.credited:
                            # Обновляем статус
                            await payment_repo.update_payment_status(payment.id, "success")

                            # Зачисляем генерации
                            success = await user_repo.update_generations(
                                payment.telegram_id,
                                payment.generations
                            )

                            if success:
                                # Отмечаем как зачисленный
                                await payment_repo.mark_as_credited(payment.id)

                                # Получаем новый баланс
                                new_balance = await user_repo.get_user_balance(
                                    payment.telegram_id
                                )

                                # Отправляем сообщение пользователю
                                try:
                                    await bot.send_message(
                                        payment.telegram_id,
                                        "✅ <b>Платеж успешно обработан!</b>\n\n"
                                        f"💎 Зачислено генераций: <b>+{payment.generations}</b>\n"
                                        f"💳 Ваш новый баланс: <b>{new_balance} генераций</b>\n\n"
                                        f"📸 Теперь можешь отправлять фото для создания елочных игрушек!"
                                    )

                                    logger.info(
                                        f"Автоматически зачислены генерации по платежу {payment.id}: "
                                        f"+{payment.generations} для пользователя {payment.telegram_id}"
                                    )
                                except Exception as e:
                                    logger.error(
                                        f"Ошибка при отправке сообщения пользователю {payment.telegram_id}: {e}"
                                    )

                        elif robokassa_status == "failed":
                            # Обновляем статус на failed
                            await payment_repo.update_payment_status(payment.id, "failed")
                            logger.info(f"Платеж {payment.id} отклонен")

                    except Exception as e:
                        logger.error(f"Ошибка при проверке платежа {payment.id}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Ошибка в фоновой задаче проверки платежей: {e}", exc_info=True)
            await asyncio.sleep(60)  # Ждем минуту перед следующей попыткой


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Бот запущен")
    logger.info(f"Модель OpenRouter: {config.openrouter.model}")
    logger.info(f"Начальные генерации: {config.generations.initial_count}")
    logger.info(f"Реферальный бонус: {config.generations.referral_bonus}")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Остановка бота...")
    await database.close()
    logger.info("Бот остановлен")


async def main():
    """Основная функция запуска бота"""
    try:
        # Инициализация бота
        bot = Bot(
            token=config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        # Инициализация диспетчера с FSM storage
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Регистрация обработчиков startup и shutdown
        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        # Подключение роутеров
        dp.include_router(start.router)
        dp.include_router(menu.router)
        dp.include_router(admin_promo_code.router)
        dp.include_router(promo_code.router)
        dp.include_router(image_processing.router)

        logger.info("Роутеры подключены")

        # Запуск фоновой задачи для автоматической проверки платежей
        payment_check_task = asyncio.create_task(check_pending_payments(bot))
        logger.info("Запущена фоновая задача проверки платежей")

        # Запуск polling
        logger.info("Начало polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем (Ctrl+C)")
    except Exception as e:
        logger.error(f"Неожиданная ошибка: {e}", exc_info=True)
        sys.exit(1)
