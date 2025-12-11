"""
Клавиатуры для онбординга новых пользователей
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_skip_photo_keyboard():
    """Клавиатура для пропуска загрузки фото"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="onboarding:skip_photo")]
    ])


def get_start_onboarding_keyboard():
    """Клавиатура для начала онбординга"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Продолжить", callback_data="onboarding:start")]
    ])
