"""
Клавиатуры для раздела параметров
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_measurements_keyboard():
    """Клавиатура для начала ввода параметров"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✏️ Указать параметры",
            callback_data="measurements:start"
        )],
        [InlineKeyboardButton(
            text="◀️ В главное меню",
            callback_data="main_menu"
        )]
    ])


def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="measurements:cancel"
        )]
    ])


def get_measurements_actions_keyboard():
    """Клавиатура с действиями над параметрами"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✏️ Изменить параметры",
            callback_data="measurements:edit_menu"
        )],
        [InlineKeyboardButton(
            text="◀️ В главное меню",
            callback_data="main_menu"
        )]
    ])


def get_edit_measurements_keyboard():
    """Клавиатура выбора параметра для редактирования"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📏 Рост", callback_data="measurements:edit:height"),
            InlineKeyboardButton(text="👚 Грудь", callback_data="measurements:edit:chest")
        ],
        [
            InlineKeyboardButton(text="👖 Талия", callback_data="measurements:edit:waist"),
            InlineKeyboardButton(text="🍑 Бедра", callback_data="measurements:edit:hips")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="measurements:view")]
    ])


def get_go_to_catalog_keyboard():
    """Клавиатура с кнопкой перехода в каталог"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Перейти в каталог",
            callback_data="back:categories"
        )]
    ])
