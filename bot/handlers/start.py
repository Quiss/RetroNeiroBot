"""Обработчик команды /start"""
from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.utils.deep_linking import decode_payload

from bot.config import config
from bot.database import get_db_session
from bot.repositories.user_repository import UserRepository
from bot.keyboards import get_main_menu_keyboard
from bot.logger import logger

router = Router()


@router.message(CommandStart(deep_link=True))
async def cmd_start_with_referral(message: Message):
    """
    Обработка команды /start с реферальной ссылкой
    Формат: /start ref_$telegramId
    """
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username

    # Извлекаем реферальный код из deep link
    referral_code = message.text.split()[1] if len(message.text.split()) > 1 else None

    referrer_telegram_id = None
    if referral_code and referral_code.startswith("ref_"):
        try:
            referrer_telegram_id = int(referral_code[4:])  # Убираем "ref_"
            logger.info(f"Реферальный переход: {telegram_id} от {referrer_telegram_id}")
        except ValueError:
            logger.warning(f"Некорректный реферальный код: {referral_code}")

    async with get_db_session() as session:
        user_repo = UserRepository(session)

        # Проверяем, существует ли пользователь
        existing_user = await user_repo.get_user_by_telegram_id(telegram_id)

        if existing_user:
            # Пользователь уже зарегистрирован
            await message.answer(
                f"🎬 С возвращением, {first_name}!\n\n"
                f"✨ Рады видеть тебя снова!\n\n"
                f"📸 Отправь фото, чтобы создать ретро фотографию в стиле 90х, "
                f"или воспользуйся меню ниже 👇",
                reply_markup=get_main_menu_keyboard(is_admin=existing_user.is_admin)
            )
            logger.info(f"Повторный запуск от пользователя: {telegram_id}")
            return

        # Создаем нового пользователя
        await user_repo.create_user(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            referral_telegram_id=referrer_telegram_id,
            initial_generations=config.generations.initial_count,
        )

        # Если есть реферер, начисляем ему бонус
        if referrer_telegram_id and referrer_telegram_id != telegram_id:
            # Проверяем, существует ли реферер
            referrer = await user_repo.get_user_by_telegram_id(referrer_telegram_id)
            if referrer:
                await user_repo.add_referral_bonus(
                    referrer_telegram_id=referrer_telegram_id,
                    bonus_generations=config.generations.referral_bonus,
                )
                logger.info(
                    f"Начислен реферальный бонус: {referrer_telegram_id} "
                    f"получил {config.generations.referral_bonus} генераций"
                )

        # Приветственное сообщение
        welcome_message = (
            f"✨ Привет, {first_name}! ✨\n\n"
            f"🎬 Добро пожаловать в бот для создания ретро фотографий в стиле 90х!\n\n"
            f"🎁 На твоём счету: <b>{config.generations.initial_count} бесплатных генераций</b>\n\n"
            f"📸 <b>Как это работает:</b>\n"
            f"1️⃣ Отправь мне свою фотографию\n"
            f"2️⃣ Подожди немного (это магия!)\n"
            f"3️⃣ Получи винтажную фотографию в стиле 90х годов\n\n"
            f"🎨 Мы превратим твоё фото в атмосферную ретро фотографию с эффектом плёнки!\n\n"
            f"💫 Отправь фото прямо сейчас или воспользуйся меню ниже 👇"
        )

        await message.answer(
            welcome_message,
            reply_markup=get_main_menu_keyboard()
        )


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработка команды /start без параметров"""
    telegram_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username

    async with get_db_session() as session:
        user_repo = UserRepository(session)

        # Проверяем, существует ли пользователь
        existing_user = await user_repo.get_user_by_telegram_id(telegram_id)

        if existing_user:
            # Пользователь уже зарегистрирован
            await message.answer(
                f"🎬 С возвращением, {first_name}!\n\n"
                f"✨ Рады видеть тебя снова!\n\n"
                f"📸 Отправь фото, чтобы создать ретро фотографию в стиле 90х, "
                f"или воспользуйся меню ниже 👇",
                reply_markup=get_main_menu_keyboard(is_admin=existing_user.is_admin)
            )
            logger.info(f"Повторный запуск от пользователя: {telegram_id}")
            return

        # Создаем нового пользователя
        await user_repo.create_user(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            initial_generations=config.generations.initial_count,
        )

        # Приветственное сообщение
        welcome_message = (
            f"✨ Привет, {first_name}! ✨\n\n"
            f"🎬 Добро пожаловать в бот для создания ретро фотографий в стиле 90х!\n\n"
            f"🎁 На твоём счету: <b>{config.generations.initial_count} бесплатных генераций</b>\n\n"
            f"📸 <b>Как это работает:</b>\n"
            f"1️⃣ Отправь мне свою фотографию\n"
            f"2️⃣ Подожди немного (это магия!)\n"
            f"3️⃣ Получи винтажную фотографию в стиле 90х годов\n\n"
            f"🎨 Мы превратим твоё фото в атмосферную ретро фотографию с эффектом плёнки!\n\n"
            f"💫 Отправь фото прямо сейчас или воспользуйся меню ниже 👇"
        )

        await message.answer(
            welcome_message,
            reply_markup=get_main_menu_keyboard()
        )
