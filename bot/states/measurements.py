"""
FSM состояния для ввода параметров пользователя
"""
from aiogram.fsm.state import State, StatesGroup


class MeasurementStates(StatesGroup):
    """Состояния для ввода параметров тела"""
    waiting_height = State()
    waiting_chest = State()
    waiting_waist = State()
    waiting_hips = State()

    # Состояния для редактирования конкретного параметра
    editing_height = State()
    editing_chest = State()
    editing_waist = State()
    editing_hips = State()
