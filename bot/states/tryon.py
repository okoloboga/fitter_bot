"""
FSM состояния для примерки одежды
"""
from aiogram.fsm.state import State, StatesGroup


class TryOnStates(StatesGroup):
    """Состояния процесса примерки"""
    waiting_tryon_mode = State()  # Выбор режима примерки (весь образ / только товар)
    waiting_consent = State()  # Ожидание согласия на обработку фото
    waiting_photo = State()    # Ожидание загрузки фото
    validating_photo = State() # Валидация фото
    selecting_photo = State()  # Выбор фото из сохраненных
    selecting_model = State()  # Выбор модели генерации (быстрая / качественная)
