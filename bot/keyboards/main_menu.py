"""
Главное меню бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu():
    """Получить клавиатуру главного меню"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog")],
            [InlineKeyboardButton(text="⭐️ Избранное", callback_data="favorites")],
            [InlineKeyboardButton(text="📐 Мои параметры", callback_data="measurements")],
            [InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")],
        ],
    )
    return keyboard
