"""
Клавиатуры для раздела параметров
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="measurements:cancel"
        )]
    ])


def get_measurements_menu_keyboard():
    """Клавиатура главного меню параметров"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="✏️ Добавить/изменить параметры",
            callback_data="measurements:edit_menu"
        )],
        [InlineKeyboardButton(
            text="◀️ В главное меню",
            callback_data="main_menu"
        )]
    ])


def get_edit_measurements_keyboard():
    """Клавиатура выбора параметра для редактирования (все 12 параметров)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📏 Рос. размер", callback_data="measurements:edit:russian_size"),
        ],
        [
            InlineKeyboardButton(text="👔 Длина плеч", callback_data="measurements:edit:shoulder_length"),
            InlineKeyboardButton(text="👔 Ширина спины", callback_data="measurements:edit:back_width")
        ],
        [
            InlineKeyboardButton(text="👕 Длина рукава", callback_data="measurements:edit:sleeve_length"),
            InlineKeyboardButton(text="👕 Длина по спинке", callback_data="measurements:edit:back_length")
        ],
        [
            InlineKeyboardButton(text="👚 Обхват груди", callback_data="measurements:edit:chest"),
            InlineKeyboardButton(text="👖 Обхват талии", callback_data="measurements:edit:waist")
        ],
        [
            InlineKeyboardButton(text="🍑 Обхват бедер", callback_data="measurements:edit:hips"),
            InlineKeyboardButton(text="👖 Длина брюк", callback_data="measurements:edit:pants_length")
        ],
        [
            InlineKeyboardButton(text="⚡ Обхват в поясе", callback_data="measurements:edit:waist_girth"),
        ],
        [
            InlineKeyboardButton(text="📐 Высота посадки", callback_data="measurements:edit:rise_height"),
            InlineKeyboardButton(text="📐 Посадка сзади", callback_data="measurements:edit:back_rise_height")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="measurements")]
    ])


def get_go_to_catalog_keyboard():
    """Клавиатура с кнопкой перехода в каталог"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Перейти в каталог",
            callback_data="back:categories"
        )]
    ])
