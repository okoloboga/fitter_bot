"""
Клавиатуры для каталога товаров
"""
import logging
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict

logger = logging.getLogger(__name__)


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
    logger.info(f"get_product_keyboard received product data: {product}")

    fav_button_text = "❌ Убрать из избранного" if is_favorite else "⭐️ В избранное"
    fav_action = "remove" if is_favorite else "add"
    product_id = product['product_id']
    
    buttons = []

    # 1-й ряд: Избранное и Все фото
    buttons.append([
        InlineKeyboardButton(
            text=fav_button_text,
            callback_data=f"fav:{fav_action}:{product_id}"
        ),
        InlineKeyboardButton(
            text="📸 Все фото",
            callback_data=f"photos:{product_id}:{category_id}:{current_index}"
        )
    ])

    # 2-й ряд: Маркетплейсы
    marketplace_row = []
    wb_link = product.get('wb_link')
    ozon_link = product.get('ozon_url')
    shop_url = product.get('shop_url')
    logger.info(f"Checking marketplace links. WB: '{wb_link}' (type: {type(wb_link)}), Ozon: '{ozon_link}' (type: {type(ozon_link)}), Shop: '{shop_url}' (type: {type(shop_url)})")

    if wb_link and isinstance(wb_link, str) and wb_link.strip():
        marketplace_row.append(InlineKeyboardButton(
            text="Wildberries",
            url=wb_link
        ))
    
    if ozon_link and isinstance(ozon_link, str) and ozon_link.strip():
        marketplace_row.append(InlineKeyboardButton(
            text="Ozon",
            url=ozon_link
        ))

    if shop_url and isinstance(shop_url, str) and shop_url.strip():
        marketplace_row.append(InlineKeyboardButton(
            text="Магазин",
            url=shop_url
        ))
    
    if marketplace_row:
        buttons.append(marketplace_row)

    # 3-й ряд: Примерка
    buttons.append([
        InlineKeyboardButton(
            text="👗 Примерить",
            callback_data=f"tryon:start:catalog:{product_id}:{category_id}:{current_index}"
        )
    ])

    # 4-й ряд: Навигация
    nav_row = []
    if total_count > 1:
        # Кнопка назад
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
        nav_row.append(InlineKeyboardButton(
            text="▶️",
            callback_data=f"nav:{category_id}:{current_index}:next"
        ))
        buttons.append(nav_row)

    # 5-й ряд: Кнопка возврата к категориям
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


def get_favorites_product_keyboard(product: Dict, current_index: int, total_count: int):
    """Клавиатура для товара в избранном"""
    logger.info(f"get_favorites_product_keyboard received product data: {product}")
    product_id = product['product_id']
    
    buttons = []

    # 1-й ряд: Избранное и Все фото
    buttons.append([
        InlineKeyboardButton(
            text="❌ Убрать из избранного",
            callback_data=f"fav:remove:{product_id}"
        ),
        InlineKeyboardButton(
            text="📸 Все фото",
            callback_data=f"photos_fav:{product_id}:{current_index}"
        )
    ])

    # 2-й ряд: Маркетплейсы
    marketplace_row = []
    wb_link = product.get('wb_link')
    ozon_link = product.get('ozon_url')
    shop_url = product.get('shop_url')
    logger.info(f"Checking marketplace links for favorite. WB: '{wb_link}', Ozon: '{ozon_link}', Shop: '{shop_url}'")

    if wb_link and isinstance(wb_link, str) and wb_link.strip():
        marketplace_row.append(InlineKeyboardButton(
            text="Wildberries",
            url=wb_link
        ))
    
    if ozon_link and isinstance(ozon_link, str) and ozon_link.strip():
        logger.info("Ozon link is valid for favorite, creating button.")
        marketplace_row.append(InlineKeyboardButton(
            text="Ozon",
            url=ozon_link
        ))
    else:
        logger.info("Ozon link is invalid or empty for favorite, skipping button.")

    if shop_url and isinstance(shop_url, str) and shop_url.strip():
        marketplace_row.append(InlineKeyboardButton(
            text="Магазин",
            url=shop_url
        ))
    
    if marketplace_row:
        buttons.append(marketplace_row)

    # 3-й ряд: Примерка
    buttons.append([
        InlineKeyboardButton(
            text="👗 Примерить",
            callback_data=f"tryon:start:favorites:{product_id}::{current_index}"
        )
    ])

    # 4-й ряд: Навигация
    nav_row = []
    if total_count > 1:
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

    # 5-й ряд: Кнопка возврата в главное меню
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
