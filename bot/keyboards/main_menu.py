"""
Главное меню бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_main_menu(has_tryon_history: bool = False):
    """Получить клавиатуру главного меню

    Args:
        has_tryon_history: True если у пользователя есть история примерок
    """
    buttons = [
        [
            InlineKeyboardButton(text="🛍 Каталог", callback_data="catalog"),
            InlineKeyboardButton(text="⭐️ Избранное", callback_data="favorites")
        ],
        [InlineKeyboardButton(text="📐 Мои параметры", callback_data="measurements")],
    ]

    # Добавляем кнопку истории примерок если есть история
    if has_tryon_history:
        buttons.append([InlineKeyboardButton(text="📜 История примерок", callback_data="tryon_history")])

    buttons.append([InlineKeyboardButton(text="ℹ️ О боте", callback_data="about")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard
