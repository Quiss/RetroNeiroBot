"""Обработчики пунктов меню"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

from decimal import Decimal
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import config
from bot.database import get_db_session
from bot.repositories.user_repository import UserRepository
from bot.repositories.payment_repository import PaymentRepository
from bot.services.robokassa import robokassa_service
from bot.keyboards import (
    get_pricing_keyboard,
    get_referral_keyboard,
    get_info_keyboard,
    get_main_menu_keyboard,
)
from bot.logger import logger

router = Router()


@router.message(F.text == "💰 Проверить баланс")
async def check_balance(message: Message):
    """Обработка кнопки 'Проверить баланс'"""
    telegram_id = message.from_user.id

    async with get_db_session() as session:
        user_repo = UserRepository(session)
        user = await user_repo.get_user_by_telegram_id(telegram_id)

        if user is not None:
            balance = user.available_generation
            balance_emoji = "🎉" if balance > 0 else "😔"
            balance_message = (
                f"{balance_emoji} <b>Твой баланс генераций</b>\n\n"
                f"💎 Доступно: <b>{balance} генераций</b>\n\n"
                f"📸 1 фото = 1 генерация\n"
                f"✨ Каждая фотография превратится в уникальное ретро фото в стиле 90х!\n\n"
            )

            if balance == 0:
                balance_message += (
                    f"😊 <b>Генерации закончились?</b>\n"
                    f"Ты можешь:\n"
                    f"💳 Купить генерации\n"
                    f"🤝 Пригласить друзей и получить бонусы"
                )
            else:
                balance_message += (
                    f"🎬 Отправь фото, чтобы создать ретро фотографию в стиле 90х!"
                )

            await message.answer(
                balance_message,
                reply_markup=get_main_menu_keyboard(is_admin=user.is_admin)
            )
            logger.info(f"Проверка баланса: {telegram_id} = {balance}")
        else:
            await message.answer(
                "Ошибка при получении баланса. Попробуй позже.",
                reply_markup=get_main_menu_keyboard()
            )
            logger.error(f"Не удалось получить баланс для {telegram_id}")


@router.message(F.text == "💳 Купить генерации")
async def buy_generations(message: Message):
    """Обработка кнопки 'Купить генерации'"""
    telegram_id = message.from_user.id

    async with get_db_session() as session:
        user_repo = UserRepository(session)
        balance = await user_repo.get_user_balance(telegram_id)

        if balance is not None:
            purchase_message = (
                f"💳 <b>Покупка генераций</b>\n\n"
                f"💎 Текущий баланс: <b>{balance} генераций</b>\n\n"
                f"🎨 Каждая генерация = одно уникальное ретро фото в стиле 90х!\n\n"
                f"📦 <b>Выбери подходящий тариф:</b>"
            )

            keyboard = get_pricing_keyboard(config.pricing)

            await message.answer(purchase_message, reply_markup=keyboard)
            logger.info(f"Открыто меню покупки: {telegram_id}")
        else:
            await message.answer("Ошибка при загрузке тарифов. Попробуй позже.")


@router.callback_query(F.data.startswith("buy_"))
async def process_purchase(callback: CallbackQuery):
    """Обработка выбора тарифа и создание платежа"""
    await callback.answer()

    telegram_id = callback.from_user.id
    generations_str = callback.data.split("_")[1]

    try:
        generations = int(generations_str)
    except ValueError:
        await callback.message.answer("❌ Ошибка: неверный формат тарифа.")
        return

    # Находим тариф в конфигурации
    selected_tier = None
    for tier in config.pricing:
        if tier.generations == generations:
            selected_tier = tier
            break

    if not selected_tier:
        await callback.message.answer("❌ Ошибка: тариф не найден.")
        return

    # Создаем платеж
    async with get_db_session() as session:
        payment_repo = PaymentRepository(session)

        try:
            # Создаем запись о платеже в БД
            payment = await payment_repo.create_payment(
                telegram_id=telegram_id,
                payment_driver=config.payment.driver,
                sum=Decimal(str(selected_tier.price)),
                generations=selected_tier.generations,
            )

            # Создаем ссылку на оплату через Robokassa
            payment_link, numeric_inv_id = robokassa_service.create_payment_link(
                invoice_id=str(payment.id),
                amount=Decimal(str(selected_tier.price)),
                description=f"Покупка {selected_tier.generations} генераций"
            )

            # Обновляем платеж ссылкой и числовым invoice_id
            payment.payment_link = payment_link
            payment.invoice_id = str(numeric_inv_id)
            await session.commit()

            # Создаем клавиатуру с кнопками
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💳 Оплатить",
                            url=payment_link
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔄 Проверить платеж",
                            callback_data=f"check_payment_{payment.id}"
                        )
                    ]
                ]
            )

            # Отправляем сообщение пользователю
            await callback.message.answer(
                f"💳 <b>Платеж создан!</b>\n\n"
                f"💎 Генераций: <b>{selected_tier.generations}</b>\n"
                f"💰 Сумма: <b>{selected_tier.price} {selected_tier.currency} {selected_tier.subtext}</b>\n\n"
                f"📝 ID платежа: <code>{payment.id}</code>\n\n"
                f"Нажми на кнопку <b>'Оплатить'</b> для перехода к оплате.\n"
                f"После оплаты нажми <b>'Проверить платеж'</b> для зачисления генераций.",
                reply_markup=keyboard
            )

            logger.info(
                f"Создан платеж {payment.id} для {telegram_id}: "
                f"{selected_tier.generations} генераций за {selected_tier.price} руб"
            )

        except Exception as e:
            logger.error(f"Ошибка при создании платежа: {e}", exc_info=True)
            await callback.message.answer(
                "⚠️ <b>Ошибка при создании платежа</b>\n\n"
                "Попробуй ещё раз или обратись в поддержку."
            )


@router.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery):
    """Проверка статуса платежа"""
    # Отвечаем на callback сразу, чтобы убрать "часики" в Telegram
    # Игнорируем ошибку если callback уже истек
    try:
        await callback.answer()
    except TelegramBadRequest as e:
        if "query is too old" not in str(e):
            raise  # Если это другая ошибка - пробрасываем дальше
        logger.warning(f"Callback уже истек для пользователя {callback.from_user.id}")

    telegram_id = callback.from_user.id
    payment_id_str = callback.data.split("_")[-1]

    try:
        import uuid
        payment_id = uuid.UUID(payment_id_str)
    except ValueError:
        await callback.message.answer("❌ Ошибка: неверный ID платежа.")
        return

    async with get_db_session() as session:
        payment_repo = PaymentRepository(session)
        user_repo = UserRepository(session)

        # Получаем платеж
        payment = await payment_repo.get_payment_by_id(payment_id)

        if not payment:
            await callback.message.answer(
                "❌ <b>Платеж не найден</b>\n\n"
                "Не удалось найти информацию о платеже."
            )
            return

        if payment.telegram_id != telegram_id:
            await callback.message.answer(
                "⛔️ <b>Доступ запрещён</b>\n\n"
                "Этот платеж принадлежит другому пользователю."
            )
            return

        # Если статус pending, пытаемся проверить через API Robokassa
        # (работает только если есть inv_id от Robokassa)
        if payment.payment_status == "pending" and payment.invoice_id and payment.invoice_id.isdigit():
            logger.info(f"Проверка статуса платежа {payment.id} через API Robokassa")

            try:
                # Получаем актуальный статус из Robokassa
                robokassa_status = await robokassa_service.check_payment_status(
                    payment.invoice_id
                )

                # Обновляем статус в БД если он изменился
                if robokassa_status and robokassa_status != payment.payment_status:
                    await payment_repo.update_payment_status(payment.id, robokassa_status)
                    payment.payment_status = robokassa_status  # Обновляем локальный объект
                    logger.info(
                        f"Статус платежа {payment.id} обновлен на '{robokassa_status}'"
                    )
            except Exception as e:
                logger.warning(f"Не удалось проверить статус через API: {e}")

        # ВАЖНО: Обновляем payment из БД, чтобы получить актуальное значение credited
        # (на случай если фоновая задача уже зачислила генерации)
        await session.refresh(payment)

        # Проверяем статус
        if payment.payment_status == "success":
            # ВАЖНО: Проверяем credited - может быть уже зачислено фоновой задачей
            if payment.credited:
                # Генерации уже зачислены (возможно фоновой задачей)
                new_balance = await user_repo.get_user_balance(telegram_id)
                try:
                    await callback.message.edit_text(
                        "✅ <b>Платеж уже обработан!</b>\n\n"
                        f"💎 Генерации уже зачислены на твой счёт.\n"
                        f"💳 Текущий баланс: <b>{new_balance} генераций</b>\n\n"
                        f"📸 Можешь отправлять фото для создания ретро фотографий в стиле 90х!"
                    )
                except TelegramBadRequest:
                    try:
                        await callback.answer("✅ Генерации уже на счёте!", show_alert=False)
                    except TelegramBadRequest:
                        pass  # Callback истек, ничего не делаем

                logger.info(
                    f"Платеж {payment.id} уже был обработан ранее "
                    f"(возможно автоматически)"
                )
                return

            # Генерации еще не зачислены - зачисляем сейчас
            logger.info(
                f"Зачисление генераций по платежу {payment.id} вручную "
                f"через кнопку проверки"
            )

            success = await user_repo.update_generations(
                telegram_id, payment.generations
            )

            if success:
                # Отмечаем платеж как зачисленный
                await payment_repo.mark_as_credited(payment.id)

                # Получаем новый баланс
                new_balance = await user_repo.get_user_balance(telegram_id)

                try:
                    await callback.message.edit_text(
                        "✅ <b>Платеж успешно обработан!</b>\n\n"
                        f"💎 Зачислено генераций: <b>+{payment.generations}</b>\n"
                        f"💳 Ваш новый баланс: <b>{new_balance} генераций</b>\n\n"
                        f"📸 Теперь можешь отправлять фото для создания ретро фотографий в стиле 90х!"
                    )
                except TelegramBadRequest:
                    try:
                        await callback.answer("✅ Генерации уже зачислены!", show_alert=False)
                    except TelegramBadRequest:
                        pass  # Callback истек, ничего не делаем

                logger.info(
                    f"Зачислены генерации по платежу {payment.id}: "
                    f"+{payment.generations} для пользователя {telegram_id}"
                )
            else:
                try:
                    await callback.message.edit_text(
                        "⚠️ <b>Ошибка при зачислении генераций</b>\n\n"
                        "Платеж успешно оплачен, но возникла ошибка при зачислении.\n"
                        "Обратись в поддержку, указав ID платежа: "
                        f"<code>{payment.id}</code>"
                    )
                except TelegramBadRequest:
                    try:
                        await callback.answer("⚠️ Обратись в поддержку", show_alert=False)
                    except TelegramBadRequest:
                        pass  # Callback истек, ничего не делаем
            return

        elif payment.payment_status == "failed":
            try:
                await callback.message.edit_text(
                    "❌ <b>Платеж отклонён</b>\n\n"
                    "К сожалению, этот платеж был отклонён.\n\n"
                    "Попробуй создать новый платеж через меню '💳 Купить генерации'."
                )
            except TelegramBadRequest:
                try:
                    await callback.answer("❌ Платеж уже отклонён", show_alert=False)
                except TelegramBadRequest:
                    pass  # Callback истек, ничего не делаем
            return

        # Если статус pending - показываем что ожидаем оплату
        # Создаем клавиатуру с кнопками
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="💳 Оплатить",
                        url=payment.payment_link
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Проверить платеж",
                        callback_data=f"check_payment_{payment.id}"
                    )
                ]
            ]
        )

        try:
            await callback.message.edit_text(
                "⏳ <b>Платеж ожидает оплаты</b>\n\n"
                f"💳 Статус: <b>Ожидает подтверждения</b>\n"
                f"💎 Генераций: <b>{payment.generations}</b>\n"
                f"💰 Сумма: <b>{payment.sum} ₽</b>\n\n"
                f"📝 Если ты уже оплатил, подожди несколько минут и нажми 'Проверить платеж' снова.\n\n"
                f"💡 <b>Важно:</b> После успешной оплаты генерации будут автоматически зачислены на твой счёт.",
                reply_markup=keyboard
            )
        except TelegramBadRequest:
            # Сообщение не изменилось, показываем уведомление
            try:
                await callback.answer(
                    "⏳ Статус платежа не изменился. Попробуй позже.",
                    show_alert=False
                )
            except TelegramBadRequest:
                pass  # Callback истек, ничего не делаем

        logger.info(
            f"Проверка платежа {payment_id} пользователем {telegram_id}: "
            f"статус {payment.payment_status}"
        )


@router.message(F.text == "🤝 Бонусы за друзей")
async def referral_program(message: Message):
    """Обработка кнопки 'Бонусы за друзей'"""
    telegram_id = message.from_user.id

    async with get_db_session() as session:
        user_repo = UserRepository(session)
        referral_stats = await user_repo.get_referral_stats(telegram_id)

        if referral_stats is not None:
            # Формируем реферальную ссылку
            referral_link = f"https://t.me/{config.bot.bot_username}?start=ref_{telegram_id}"

            referral_message = (
                f"🤝 <b>Бонусы за друзей</b>\n\n"
                f"💝 Приглашай друзей и получайте бонусы вместе!\n\n"
                f"🎁 <b>Как это работает:</b>\n"
                f"1️⃣ Отправь свою ссылку другу\n"
                f"2️⃣ Друг запускает бота по твоей ссылке\n"
                f"3️⃣ Вы оба получаете бонусные генерации!\n\n"
                f"🔗 <b>Твоя личная ссылка:</b>\n"
                f"<code>{referral_link}</code>\n\n"
                f"📊 <b>Статистика:</b>\n"
                f"✨ Всего получено от рефералов: <b>{referral_stats} генераций</b>\n\n"
                f"💫 Нажми на кнопку ниже, чтобы поделиться ссылкой!"
            )

            keyboard = get_referral_keyboard(referral_link)

            await message.answer(referral_message, reply_markup=keyboard)
            logger.info(f"Открыта программа 'Бонусы за друзей': {telegram_id}")
        else:
            await message.answer("Ошибка при загрузке информации. Попробуй позже.")


@router.message(F.text == "🎨 Другие обработки")
async def other_processing(message: Message):
    """Обработка кнопки 'Другие обработки'"""
    other_processing_message = (
        "🎨 <b>Другие обработки</b>\n\n"
        "✨ Здесь собраны другие популярные обработки, которые вы можете создать!\n\n"
        "🎄 Попробуйте разные стили и эффекты для ваших фотографий:\n"
        "👇 Выберите интересующую обработку из списка ниже"
    )

    # Динамически создаем кнопки из конфига
    keyboard_buttons = [
        [InlineKeyboardButton(text=button.text, url=button.url)]
        for button in config.other_processing_buttons
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

    await message.answer(other_processing_message, reply_markup=keyboard)
    logger.info(f"Открыто меню 'Другие обработки': {message.from_user.id}")


@router.message(F.text == "💬 Поддержка")
async def support(message: Message):
    """Обработка кнопки 'Поддержка'"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    support_message = (
        f"💬 Поддержка\n\n"
        f"Если у тебя возникли вопросы или проблемы, нажми на кнопку ниже:"
    )

    # Создаем inline кнопку с прямой ссылкой
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💬 Написать в поддержку",
                    url=config.bot.support_url
                )
            ]
        ]
    )

    await message.answer(support_message, reply_markup=keyboard)
    logger.info(f"Открыто меню поддержки: {message.from_user.id}")


@router.message(F.text == "ℹ️ Информация")
async def information(message: Message):
    """Обработка кнопки 'Информация'"""
    info_message = (
        f"ℹ️ <b>Информация о боте</b>\n\n"
        f"🎬 Мы создаём винтажные ретро фотографии в стиле 90х из ваших фото\n\n"
        f"📋 Нажми на кнопку ниже, чтобы ознакомиться с документами:"
    )

    keyboard = get_info_keyboard(config.documents)

    await message.answer(info_message, reply_markup=keyboard)
    logger.info(f"Открыто меню информации: {message.from_user.id}")
