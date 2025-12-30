"""
Скрипт для массовой рассылки сообщений пользователям

Использование:
    # Рассылка всем пользователям
    python -m bot.broadcast --file upgrade.txt

    # Рассылка конкретным пользователям (для тестирования)
    python -m bot.broadcast --file upgrade.txt --users 123456789,987654321

    # Тестовый режим (рекомендуется использовать первым)
    python -m bot.broadcast --file upgrade.txt --test
"""

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from sqlalchemy import select

from bot.config import config
from bot.database import get_db_session
from bot.models.user import User
from bot.logger import logger


def personalize_message(message_text: str, user: User) -> str:
    """
    Персонализировать сообщение для конкретного пользователя

    Доступные переменные:
    - :first_name - имя пользователя
    - :last_name - фамилия пользователя
    - :username - username пользователя

    Args:
        message_text: Исходный текст с переменными
        user: Объект пользователя

    Returns:
        Персонализированный текст сообщения
    """
    # Значения по умолчанию
    first_name = user.first_name or "пользователь"
    last_name = user.last_name or ""
    username = user.username or "пользователь"

    # Заменяем переменные
    personalized = message_text.replace(":first_name", first_name)
    personalized = personalized.replace(":last_name", last_name)
    personalized = personalized.replace(":username", username)

    return personalized


async def get_all_users():
    """
    Получить всех пользователей из базы данных

    Returns:
        List[User]: Список всех пользователей
    """
    async with get_db_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        logger.info(f"✅ Всего загружено пользователей: {len(users)}")
        return list(users)


async def broadcast_message(
    message_text: str, target_users: list = None, test_mode: bool = False
):
    """
    Отправить сообщение пользователям

    Args:
        message_text: Текст сообщения для рассылки
        target_users: Список telegram_id для рассылки (если None - всем)
        test_mode: Если True, только показывает кому будет отправлено, без реальной отправки
    """
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    try:
        # Получаем пользователей
        if target_users:
            # Фильтруем только указанных пользователей
            logger.info(
                f"🎯 Рассылка для конкретных пользователей: {', '.join(map(str, target_users))}"
            )
            async with get_db_session() as session:
                result = await session.execute(
                    select(User).where(User.telegram_id.in_(target_users))
                )
                users = result.scalars().all()
        else:
            # Получаем всех пользователей
            logger.info("📢 Получение всех пользователей для рассылки...")
            users = await get_all_users()

        total_users = len(users)

        # Тестовый режим - показываем информацию без отправки
        if test_mode:
            logger.info("=" * 50)
            logger.info("🧪 ТЕСТОВЫЙ РЕЖИМ - реальная отправка НЕ будет выполнена")
            logger.info("=" * 50)
            logger.info(f"📊 Будет отправлено {total_users} пользователям")
            logger.info("")
            logger.info("📝 Текст сообщения (оригинал):")
            logger.info("-" * 50)
            logger.info(message_text)
            logger.info("-" * 50)

            # Показываем пример персонализации для первого пользователя
            if users and len(users) > 0:
                logger.info("")
                logger.info("🎨 Пример персонализированного сообщения для первого пользователя:")
                logger.info("-" * 50)
                personalized_example = personalize_message(message_text, users[0])
                logger.info(personalized_example)
                logger.info("-" * 50)
                logger.info(f"Для: {users[0].first_name or 'N/A'} {users[0].last_name or ''} (@{users[0].username or 'N/A'})")

            logger.info("")
            logger.info("👥 Список получателей (первые 10):")

            for i, user in enumerate(users[:10], 1):
                telegram_id = user.telegram_id
                username = user.username or "N/A"
                first_name = user.first_name or "N/A"
                logger.info(
                    f"  {i}. telegram_id: {telegram_id} | @{username} | {first_name}"
                )

            if total_users > 10:
                logger.info(f"  ... и ещё {total_users - 10} получателей")

            logger.info("")
            logger.info("=" * 50)
            logger.info("✅ Тестовый просмотр завершён")
            logger.info(
                "💡 Для реальной отправки запустите без флага --test"
            )
            logger.info("=" * 50)
            return

        # Реальная рассылка
        logger.info(f"📊 Начинаем рассылку для {total_users} пользователей")

        success_count = 0
        failed_count = 0

        for i, user in enumerate(users, 1):
            telegram_id = user.telegram_id

            if not telegram_id:
                logger.warning(f"⚠️ Пользователь без telegram_id: {user}")
                failed_count += 1
                continue

            try:
                # Персонализируем сообщение для текущего пользователя
                personalized_text = personalize_message(message_text, user)

                await bot.send_message(
                    chat_id=telegram_id,
                    text=personalized_text
                )
                success_count += 1
                logger.info(
                    f"✅ [{i}/{total_users}] Отправлено пользователю {telegram_id}"
                )

                # Задержка между сообщениями (чтобы не превысить лимиты Telegram)
                await asyncio.sleep(0.05)  # 50ms между сообщениями

            except Exception as e:
                failed_count += 1
                logger.error(
                    f"❌ [{i}/{total_users}] Ошибка отправки пользователю {telegram_id}: {e}"
                )

        # Итоговая статистика
        logger.info("=" * 50)
        logger.info(f"📊 Рассылка завершена!")
        logger.info(f"✅ Успешно: {success_count}")
        logger.info(f"❌ Ошибок: {failed_count}")
        logger.info(f"📈 Всего: {total_users}")
        logger.info("=" * 50)

    finally:
        await bot.session.close()


def main():
    """Точка входа для скрипта"""

    # Создаём директорию для логов если её нет
    broadcast_logs_dir = Path("logs/broadcast")
    broadcast_logs_dir.mkdir(parents=True, exist_ok=True)

    # Генерируем имя лог-файла с текущей датой и временем
    now = datetime.now()
    log_filename = now.strftime("%Y-%m-%d_%H-%M-%S.txt")
    log_path = broadcast_logs_dir / log_filename

    logger.info(f"📝 Лог рассылки сохраняется в: {log_path}")

    # Настройка дополнительного логирования в файл
    logger.add(str(log_path), level="INFO")

    # Парсинг аргументов командной строки
    parser = argparse.ArgumentParser(description="Массовая рассылка сообщений")
    parser.add_argument(
        "--file",
        "-f",
        required=True,
        help="Путь к файлу с текстом сообщения (например, upgrade.txt)",
    )
    parser.add_argument(
        "--users",
        "-u",
        help="Список telegram_id через запятую для тестовой рассылки (например, 123456789,987654321)",
    )
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="Тестовый режим: показать кому и что будет отправлено без реальной отправки",
    )

    args = parser.parse_args()

    # Читаем файл с сообщением
    message_file = Path(args.file)

    if not message_file.exists():
        logger.error(f"❌ Файл не найден: {message_file}")
        sys.exit(1)

    message_text = message_file.read_text(encoding="utf-8").strip()

    if not message_text:
        logger.error("❌ Файл пустой!")
        sys.exit(1)

    logger.info(f"📄 Загружен текст сообщения из {message_file}")
    logger.info(f"📝 Длина сообщения: {len(message_text)} символов")

    # Парсим список пользователей (если указан)
    target_users = None
    if args.users:
        try:
            target_users = [int(uid.strip()) for uid in args.users.split(",")]
            logger.info(f"🎯 Целевые пользователи: {target_users}")
        except ValueError:
            logger.error("❌ Неверный формат списка пользователей!")
            sys.exit(1)

    # Запускаем рассылку
    try:
        asyncio.run(broadcast_message(message_text, target_users, args.test))
    except KeyboardInterrupt:
        logger.warning("⚠️ Рассылка прервана пользователем")
        sys.exit(0)


if __name__ == "__main__":
    main()
