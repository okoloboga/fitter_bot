"""
FSM состояния для примерки одежды
"""
from aiogram.fsm.state import State, StatesGroup


class TryOnStates(StatesGroup):
    """Состояния процесса примерки"""
    waiting_consent = State()  # Ожидание согласия на обработку фото
    waiting_photo = State()    # Ожидание загрузки фото
    validating_photo = State() # Валидация фото
    selecting_photo = State()  # Выбор фото из сохраненных
