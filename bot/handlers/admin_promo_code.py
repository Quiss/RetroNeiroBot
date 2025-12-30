"""Обработчик генерации промокодов для администраторов"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from bot.database import get_db_session
from bot.repositories.promo_code_repository import PromoCodeRepository
from bot.repositories.user_repository import UserRepository
from bot.states import AdminPromoCodeStates
from bot.logger import logger

router = Router()


@router.message(F.text == "🔧 Сгенерировать промокод")
async def start_promo_code_generation(message: Message, state: FSMContext):
    """Начало процесса генерации промокода (только для админов)"""
    telegram_id = message.from_user.id

    # Проверяем, является ли пользователь администратором
    async with get_db_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_user_by_telegram_id(telegram_id)

        if not user or not user.is_admin:
            await message.answer(
                "⛔️ <b>Доступ запрещён</b>\n\n"
                "Эта функция доступна только администраторам."
            )
            logger.warning(f"Попытка доступа к админ-функции от {telegram_id}")
            return

    await message.answer(
        "🔧 <b>Генерация промокода</b>\n\n"
        "📊 Введи количество генераций для промокода.\n\n"
        "💡 <b>Диапазон:</b> от 1 до 9999\n\n"
        "❌ Чтобы отменить, отправь /cancel"
    )

    # Устанавливаем состояние ожидания количества генераций
    await state.set_state(AdminPromoCodeStates.waiting_for_generations)

    logger.info(f"Админ {telegram_id} начал генерацию промокода")


@router.message(AdminPromoCodeStates.waiting_for_generations, F.text == "/cancel")
@router.message(AdminPromoCodeStates.waiting_for_usage_limit, F.text == "/cancel")
async def cancel_promo_code_generation(message: Message, state: FSMContext):
    """Отмена генерации промокода"""
    await state.clear()

    await message.answer(
        "❌ <b>Генерация отменена</b>\n\n"
        "Ты можешь начать генерацию промокода снова в любое время."
    )

    logger.info(f"Админ {message.from_user.id} отменил генерацию промокода")


@router.message(AdminPromoCodeStates.waiting_for_generations)
async def process_generations_count(message: Message, state: FSMContext):
    """Обработка количества генераций"""
    telegram_id = message.from_user.id

    # Проверяем, что введено число
    try:
        generations = int(message.text.strip())
    except ValueError:
        await message.answer(
            "⚠️ <b>Неверный формат</b>\n\n"
            "Пожалуйста, введи целое число от 1 до 9999.\n\n"
            "Попробуй ещё раз или отправь /cancel для отмены."
        )
        return

    # Проверяем диапазон
    if generations < 1 or generations > 9999:
        await message.answer(
            "⚠️ <b>Число вне диапазона</b>\n\n"
            "Количество генераций должно быть от 1 до 9999.\n\n"
            "Попробуй ещё раз или отправь /cancel для отмены."
        )
        return

    # Сохраняем количество генераций в состояние
    await state.update_data(generations=generations)

    await message.answer(
        f"✅ Количество генераций: <b>{generations}</b>\n\n"
        f"📊 Теперь введи лимит использований промокода.\n\n"
        f"💡 <b>Диапазон:</b> от 1 до 9999\n"
        f"(Сколько раз промокод можно активировать)\n\n"
        f"❌ Чтобы отменить, отправь /cancel"
    )

    # Переходим к следующему состоянию
    await state.set_state(AdminPromoCodeStates.waiting_for_usage_limit)

    logger.info(f"Админ {telegram_id} установил {generations} генераций")


@router.message(AdminPromoCodeStates.waiting_for_usage_limit)
async def process_usage_limit(message: Message, state: FSMContext):
    """Обработка лимита использований и создание промокода"""
    telegram_id = message.from_user.id

    # Проверяем, что введено число
    try:
        usage_limit = int(message.text.strip())
    except ValueError:
        await message.answer(
            "⚠️ <b>Неверный формат</b>\n\n"
            "Пожалуйста, введи целое число от 1 до 9999.\n\n"
            "Попробуй ещё раз или отправь /cancel для отмены."
        )
        return

    # Проверяем диапазон
    if usage_limit < 1 or usage_limit > 9999:
        await message.answer(
            "⚠️ <b>Число вне диапазона</b>\n\n"
            "Лимит использований должен быть от 1 до 9999.\n\n"
            "Попробуй ещё раз или отправь /cancel для отмены."
        )
        return

    # Получаем количество генераций из состояния
    data = await state.get_data()
    generations = data.get("generations")

    if not generations:
        await message.answer(
            "⚠️ <b>Ошибка</b>\n\n"
            "Не удалось получить количество генераций. Начни процесс заново."
        )
        await state.clear()
        return

    # Создаём промокод
    async with get_db_session() as session:
        promo_repo = PromoCodeRepository(session)
        promo_code = await promo_repo.create_promo_code(generations, usage_limit)

        # Очищаем состояние
        await state.clear()

        if promo_code:
            await message.answer(
                f"🎉 <b>Промокод успешно создан!</b>\n\n"
                f"🎫 Промокод: <code>{promo_code}</code>\n"
                f"💎 Генераций: <b>{generations}</b>\n"
                f"🔢 Лимит использований: <b>{usage_limit}</b>\n\n"
                f"✨ Промокод готов к использованию!\n"
                f"Пользователи могут активировать его через меню '💳 Купить генерации'."
            )

            logger.info(
                f"Админ {telegram_id} создал промокод {promo_code}: "
                f"{generations} генераций, лимит {usage_limit}"
            )
        else:
            await message.answer(
                "⚠️ <b>Ошибка создания промокода</b>\n\n"
                "Не удалось создать промокод. Попробуй ещё раз."
            )

            logger.error(f"Ошибка создания промокода админом {telegram_id}")
