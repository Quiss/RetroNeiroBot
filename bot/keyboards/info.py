"""Клавиатура для раздела Информация"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import DocumentsConfig


def get_info_keyboard(documents: DocumentsConfig) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру для раздела информации

    Args:
        documents: Конфигурация со ссылками на документы

    Returns:
        InlineKeyboardMarkup: Клавиатура с ссылками на документы
    """
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔒 Политика конфиденциальности",
                    url=documents.privacy_policy
                )
            ],
            [
                InlineKeyboardButton(
                    text="📜 Пользовательское соглашение",
                    url=documents.terms_of_service
                )
            ],
        ]
    )

    return keyboard
