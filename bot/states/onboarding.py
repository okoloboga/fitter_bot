"""
FSM состояния для онбординга новых пользователей
"""
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Состояния процесса онбординга"""
    waiting_russian_size = State()  # Ожидание российского размера (обязательно)
    waiting_photo = State()          # Ожидание загрузки фото (опционально)
