"""Клавиатура для реферальной программы"""
from urllib.parse import quote
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_referral_keyboard(referral_link: str) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру для реферальной программы

    Args:
        referral_link: Реферальная ссылка пользователя

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопкой приглашения
    """
    # Короткий текст с минимумом пробелов для красивого отображения
    share_text = "Попробуй бот для создания елочных игрушек из твоих фото 🎄✨"

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Пригласить друзей",
                    url=f"https://t.me/share/url?url={referral_link}&text={quote(share_text)}"
                )
            ]
        ]
    )

    return keyboard
