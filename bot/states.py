"""FSM состояния для диалогов бота"""
from aiogram.fsm.state import State, StatesGroup


class PromoCodeStates(StatesGroup):
    """Состояния для активации промокода"""

    waiting_for_code = State()


class AdminPromoCodeStates(StatesGroup):
    """Состояния для генерации промокода (админ)"""

    waiting_for_generations = State()
    waiting_for_usage_limit = State()
