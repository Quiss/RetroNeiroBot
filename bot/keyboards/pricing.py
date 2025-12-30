"""Клавиатура с тарифами покупки генераций"""
from typing import List

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.config import PricingTier


def get_pricing_keyboard(pricing: List[PricingTier]) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру с тарифами

    Args:
        pricing: Список тарифов из конфигурации

    Returns:
        InlineKeyboardMarkup: Клавиатура с тарифами
    """
    buttons = []

    for tier in pricing:
        button_text = f"{tier.generations} генераций — {tier.price}{tier.currency} {tier.subtext}"
        button = InlineKeyboardButton(
            text=button_text,
            callback_data=f"buy_{tier.generations}"
        )
        buttons.append([button])

    # Добавляем кнопку активации промокода
    promo_button = InlineKeyboardButton(
        text="🎁 Активировать промокод",
        callback_data="activate_promo_code"
    )
    buttons.append([promo_button])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    return keyboard
