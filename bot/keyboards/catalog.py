"""
Клавиатуры для каталога товаров
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict


def get_categories_keyboard(categories: List[Dict]):
    """Клавиатура с категориями товаров"""
    if not categories:
        return None

    buttons = []
    row = []
    for i, category in enumerate(categories):
        button = InlineKeyboardButton(
            text=f"{category.get('emoji', '')} {category.get('category_name', 'Без названия')}",
            callback_data=f"category:{category['category_id']}"
        )
        row.append(button)

        # По 2 кнопки в ряд
        if len(row) == 2 or i == len(categories) - 1:
            buttons.append(row.copy())
            row = []

    # Кнопка назад
    buttons.append([
        InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_product_keyboard(product: Dict, category_id: str, current_index: int,
                         total_count: int, is_favorite: bool = False):
    """Клавиатура для карточки товара"""

    fav_button_text = "❌ Убрать из избранного" if is_favorite else "⭐️ В избранное"
    fav_action = "remove" if is_favorite else "add"
    product_id = product['product_id']
    wb_link = product.get('wb_link', 'https://www.wildberries.ru/')


    buttons = [
        [InlineKeyboardButton(
            text=fav_button_text,
            callback_data=f"fav:{fav_action}:{product_id}"
        )],
        [InlineKeyboardButton(
            text="🔗 Открыть на Wildberries",
            url=wb_link
        )],
        [InlineKeyboardButton(
            text="📸 Посмотреть все фото",
            callback_data=f"photos:{product_id}:{category_id}:{current_index}"
        )],
        [InlineKeyboardButton(
            text="👗 Примерить (скоро!)",
            callback_data=f"tryon:{product_id}"
        )],
    ]

    # Навигация
    nav_row = []

    # Кнопка назад
    if current_index > 0:
        nav_row.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"nav:{category_id}:{current_index}:prev"
        ))

    # Счетчик
    nav_row.append(InlineKeyboardButton(
        text=f"({current_index + 1}/{total_count})",
        callback_data="noop"
    ))

    # Кнопка вперед
    if current_index < total_count - 1:
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"nav:{category_id}:{current_index}:next"
        ))

    buttons.append(nav_row)

    # Кнопка возврата к категориям
    buttons.append([
        InlineKeyboardButton(
            text="🔙 К категориям",
            callback_data="back:categories"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_back_to_product_keyboard(product_id: str, category_id: str, index: int):
    """Кнопка возврата к товару"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="◀️ Вернуться к товару",
            callback_data=f"back:product:{product_id}:{category_id}:{index}"
        )]
    ])


def get_favorites_product_keyboard(product_id: str, current_index: int, total_count: int):
    """Клавиатура для товара в избранном"""
    buttons = [
        [InlineKeyboardButton(
            text="❌ Убрать из избранного",
            callback_data=f"fav:remove:{product_id}"
        )],
        [InlineKeyboardButton(
            text="🔗 Открыть на Wildberries",
            url="https://www.wildberries.ru/"
        )],
        [InlineKeyboardButton(
            text="📸 Посмотреть все фото",
            callback_data=f"photos_fav:{product_id}:{current_index}"
        )],
        [InlineKeyboardButton(
            text="👗 Примерить (скоро!)",
            callback_data=f"tryon:{product_id}"
        )],
    ]

    # Навигация
    nav_row = []
    if current_index > 0:
        nav_row.append(InlineKeyboardButton(
            text="◀️",
            callback_data=f"nav_fav:{current_index}:prev"
        ))

    nav_row.append(InlineKeyboardButton(
        text=f"({current_index + 1}/{total_count})",
        callback_data="noop"
    ))

    if current_index < total_count - 1:
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"nav_fav:{current_index}:next"
        ))

    buttons.append(nav_row)

    # Кнопка возврата в главное меню
    buttons.append([
        InlineKeyboardButton(
            text="🔙 В главное меню",
            callback_data="main_menu"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_go_to_catalog_keyboard():
    """Клавиатура для перехода в каталог"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍 Перейти в каталог",
            callback_data="back:categories"
        )]
    ])
