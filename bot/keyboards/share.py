"""Клавиатура для кнопки 'Поделиться'"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_share_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру с кнопкой 'Поделиться'

    Args:
        bot_username: Имя бота (без @)

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой поделиться
    """
    share_text = (
        "🎬 Посмотри какую крутую ретро фотографию в стиле 90х я создал! "
        "Попробуй и ты создать свою винтажную фотографию!"
    )

    share_url = f"https://t.me/{bot_username}"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Поделиться",
                    url=f"https://t.me/share/url?url={share_url}&text={share_text}"
                )
            ]
        ]
    )

    return keyboard
