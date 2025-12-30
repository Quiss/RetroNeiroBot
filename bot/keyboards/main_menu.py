"""Главное меню бота (ReplyKeyboard)"""
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Создать клавиатуру главного меню

    Args:
        is_admin: Является ли пользователь администратором

    Returns:
        ReplyKeyboardMarkup: Клавиатура главного меню
    """
    keyboard_buttons = [
        [
            KeyboardButton(text="💳 Купить генерации"),
            KeyboardButton(text="💰 Проверить баланс"),
        ],
        [
            KeyboardButton(text="🎨 Другие обработки"),
            KeyboardButton(text="🤝 Бонусы за друзей"),
        ],
    ]

    # Добавляем админскую кнопку если пользователь - админ
    if is_admin:
        keyboard_buttons.append([
            KeyboardButton(text="🔧 Сгенерировать промокод"),
        ])

    keyboard_buttons.append([
        KeyboardButton(text="💬 Поддержка"),
        KeyboardButton(text="ℹ️ Информация"),
    ])

    keyboard = ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

    return keyboard
