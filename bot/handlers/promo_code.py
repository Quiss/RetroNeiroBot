"""Обработчик активации промокодов"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.database import get_db_session
from bot.repositories.promo_code_repository import PromoCodeRepository
from bot.repositories.user_repository import UserRepository
from bot.states import PromoCodeStates
from bot.logger import logger

router = Router()


@router.callback_query(F.data == "activate_promo_code")
async def start_promo_code_activation(callback: CallbackQuery, state: FSMContext):
    """Начало процесса активации промокода"""
    await callback.answer()

    await callback.message.answer(
        "🎁 <b>Активация промокода</b>\n\n"
        "💎 Введи промокод, чтобы получить бесплатные генерации!\n\n"
        "📝 Отправь промокод в ответном сообщении.\n\n"
        "❌ Чтобы отменить, отправь /cancel"
    )

    # Устанавливаем состояние ожидания промокода
    await state.set_state(PromoCodeStates.waiting_for_code)

    logger.info(f"Пользователь {callback.from_user.id} начал активацию промокода")


@router.message(PromoCodeStates.waiting_for_code, F.text == "/cancel")
async def cancel_promo_code_activation(message: Message, state: FSMContext):
    """Отмена активации промокода"""
    await state.clear()

    await message.answer(
        "❌ <b>Активация отменена</b>\n\n"
        "Ты можешь вернуться к активации промокода в любое время через меню '💳 Купить генерации'."
    )

    logger.info(f"Пользователь {message.from_user.id} отменил активацию промокода")


@router.message(PromoCodeStates.waiting_for_code)
async def process_promo_code(message: Message, state: FSMContext):
    """Обработка введённого промокода"""
    telegram_id = message.from_user.id
    code = message.text.strip().upper()

    logger.info(f"Попытка активации промокода: {telegram_id} - {code}")

    async with get_db_session() as session:
        promo_repo = PromoCodeRepository(session)

        # Активируем промокод
        success, result = await promo_repo.activate_promo_code(telegram_id, code)

        # Очищаем состояние
        await state.clear()

        if success:
            # Успешная активация
            generations_count = result

            await message.answer(
                f"🎉 <b>Промокод успешно активирован!</b>\n\n"
                f"💎 Тебе начислено: <b>{generations_count} генераций</b>\n\n"
                f"✨ Код <code>{code}</code> активирован!\n\n"
                f"📸 Отправь фото, чтобы создать свою ретро фотографию в стиле 90х!"
            )

            logger.info(
                f"Промокод {code} успешно активирован для {telegram_id}. "
                f"Начислено {generations_count} генераций"
            )

        else:
            # Обработка ошибок
            if result == "invalid":
                error_message = (
                    "❌ <b>Промокод не найден</b>\n\n"
                    "Этот промокод не существует или неверно введён.\n\n"
                    "💡 <b>Проверь:</b>\n"
                    "• Правильность написания кода\n"
                    "• Отсутствие лишних пробелов\n\n"
                    "🎁 Попробуй ввести промокод ещё раз через меню '💳 Купить генерации'."
                )
            elif result == "expired":
                error_message = (
                    "😔 <b>Промокод исчерпан</b>\n\n"
                    "К сожалению, лимит активаций этого промокода достигнут.\n\n"
                    "💡 Следи за нашими новостями, чтобы не пропустить новые промокоды!"
                )
            elif result == "already_used":
                error_message = (
                    "⚠️ <b>Промокод уже использован</b>\n\n"
                    "Ты уже активировал этот промокод ранее.\n\n"
                    "📌 Каждый промокод можно использовать только один раз."
                )
            else:
                error_message = (
                    "⚠️ <b>Ошибка активации</b>\n\n"
                    "Произошла техническая ошибка при активации промокода.\n\n"
                    "🔄 Попробуй ещё раз через несколько секунд.\n\n"
                    "Если проблема повторяется, обратись в поддержку 💬"
                )

            await message.answer(error_message)

            logger.warning(
                f"Ошибка активации промокода {code} для {telegram_id}: {result}"
            )
