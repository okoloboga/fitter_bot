"""
Обработчики каталога товаров
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from typing import Optional, List

from bot.keyboards.catalog import (
    get_categories_keyboard,
    get_product_keyboard,
    get_back_to_product_keyboard
)
from bot.utils.api_client import api_client
from bot.utils.image_processor import get_optimized_photo

router = Router()


def get_valid_photo_url(product: dict) -> Optional[str]:
    """
    Получить валидный URL фото товара с fallback логикой.

    Приоритет:
    1. collage_url
    2. photo_1_url
    3. photo_2_url
    4. photo_3_url
    5. photo_4_url
    6. photo_5_url
    7. photo_6_url

    Returns:
        Валидный URL или None, если все URL пустые
    """
    urls_to_try = [
        product.get('collage_url'),
        product.get('photo_1_url'),
        product.get('photo_2_url'),
        product.get('photo_3_url'),
        product.get('photo_4_url'),
        product.get('photo_5_url'),
        product.get('photo_6_url'),
    ]

    for url in urls_to_try:
        # Проверяем что URL не пустой и не пустая строка
        if url and isinstance(url, str) and url.strip() and url != "":
            return url

    return None


def get_all_valid_photo_urls(product: dict) -> List[str]:
    """
    Получить все валидные URL фотографий товара.

    Returns:
        Список валидных URL
    """
    urls = [
        product.get('photo_1_url'),
        product.get('photo_2_url'),
        product.get('photo_3_url'),
        product.get('photo_4_url'),
        product.get('photo_5_url'),
        product.get('photo_6_url'),
    ]

    return [url for url in urls if url and isinstance(url, str) and url.strip() and url != ""]


async def format_product_message(product: dict, user_id: int, current_index: int, total_count: int):
    """Форматировать сообщение карточки товара"""
    measurements = await api_client.get_measurements(user_id)
    size_recommendation = ""

    if measurements:
        recommendation = await api_client.recommend_size(user_id, product['product_id'])
        if recommendation and recommendation.get('success') and recommendation.get('recommended_size'):
            size_recommendation = f"\n\n✅ Рекомендуемый размер: {recommendation['recommended_size']}"
            # Optionally, add alternative size if available
            if recommendation.get('alternative_size'):
                size_recommendation += f" (возможно, подойдет {recommendation['alternative_size']})"
        elif recommendation:
            # Use the message from the recommendation service if it fails
            size_recommendation = f"\n\n⚠️ {recommendation.get('message', 'Не удалось подобрать размер')}"
        else:
            # Fallback if API call fails
            size_recommendation = "\n\n⚠️ Не удалось получить рекомендацию по размеру"
    else:
        size_recommendation = "\n\n📐 Укажи свои параметры, чтобы получить рекомендацию по размеру"

    # Ограничиваем описание (Telegram caption max 1024 символов)
    description = product.get('description', '')
    max_description_length = 600
    if len(description) > max_description_length:
        description = description[:max_description_length].rsplit(' ', 1)[0] + '...'

    message_text = f"""🧥 {product.get('name', 'Без названия')}

{description}

Размеры: {product.get('available_sizes', 'Нет данных')}{size_recommendation}

Товар {current_index + 1} из {total_count}"""

    return message_text


@router.callback_query(F.data == "back:categories")
async def back_to_categories(callback: CallbackQuery):
    """Возврат к списку категорий"""
    categories = await api_client.get_categories()
    keyboard = get_categories_keyboard(categories)
    
    # Удаляем предыдущее сообщение (карточку товара) и отправляем новое
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        "🛍 Каталог\n\nВыбери категорию:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("category:"))
async def show_category_products(callback: CallbackQuery):
    """Показать товары категории"""
    category_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    products = await api_client.get_products_by_category(category_id)

    if not products:
        await callback.answer("В этой категории пока нет товаров", show_alert=True)
        return

    product = products[0]
    message_text = await format_product_message(product, user_id, 0, len(products))
    is_fav = await api_client.check_favorite(user_id, product['product_id'])

    try:
        await callback.message.delete()
    except:
        pass

    photo_url = get_valid_photo_url(product)
    if photo_url:
        optimized_photo = await get_optimized_photo(photo_url)
        if optimized_photo:
            await callback.message.answer_photo(
                photo=optimized_photo,
                caption=message_text,
                reply_markup=get_product_keyboard(
                    product, category_id, 0, len(products), is_fav
                ),
            )
        else:
            # Fallback if optimization fails
            await callback.message.answer(
                f"📷 Не удалось загрузить фото\n\n{message_text}",
                reply_markup=get_product_keyboard(
                    product, category_id, 0, len(products), is_fav
                ),
            )
    else:
        # Fallback: отправить текстовое сообщение, если нет фото
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=get_product_keyboard(
                product,
                category_id,
                0,
                len(products),
                is_fav
            )
        )
    await callback.answer()


@router.callback_query(F.data.startswith("nav:"))
async def navigate_products(callback: CallbackQuery):
    """Навигация между товарами"""
    parts = callback.data.split(":")
    category_id = parts[1]
    current_index = int(parts[2])
    action = parts[3]
    user_id = callback.from_user.id

    products = await api_client.get_products_by_category(category_id)
    if not products:
        await callback.answer("Товары не найдены", show_alert=True)
        return

    if action == "next":
        new_index = (current_index + 1) % len(products)
    else:  # prev
        new_index = (current_index - 1 + len(products)) % len(products)

    product = products[new_index]
    message_text = await format_product_message(product, user_id, new_index, len(products))
    is_fav = await api_client.check_favorite(user_id, product['product_id'])

    photo_url = get_valid_photo_url(product)
    if not photo_url:
        await callback.answer("Фото товара недоступно", show_alert=True)
        return

    optimized_photo = await get_optimized_photo(photo_url)
    if not optimized_photo:
        await callback.answer("Не удалось загрузить фото товара", show_alert=True)
        return

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=optimized_photo,
                caption=message_text
            ),
            reply_markup=get_product_keyboard(
                product,
                category_id,
                new_index,
                len(products),
                is_fav
            )
        )
    except Exception:
        # Fallback if edit_media fails (e.g., message is too old)
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=optimized_photo,
            caption=message_text,
            reply_markup=get_product_keyboard(
                product,
                category_id,
                new_index,
                len(products),
                is_fav
            )
        )
    await callback.answer()


@router.callback_query(F.data.startswith("photos:"))
async def show_all_photos(callback: CallbackQuery):
    """Показать все фото товара"""
    parts = callback.data.split(":")
    product_id = parts[1]
    category_id = parts[2]
    index = int(parts[3])

    product = await api_client.get_product_by_id(product_id)
    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    photo_urls = get_all_valid_photo_urls(product)
    if not photo_urls:
        await callback.answer("Фотографии товара недоступны", show_alert=True)
        return

    media = [InputMediaPhoto(media=URLInputFile(url)) for url in photo_urls]

    await callback.message.answer_media_group(media=media)
    await callback.message.answer(
        "📸 Все фото товара",
        reply_markup=get_back_to_product_keyboard(product_id, category_id, index)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back:product:"))
async def back_to_product(callback: CallbackQuery):
    """Вернуться к карточке товара"""
    parts = callback.data.split(":")
    product_id = parts[2]
    category_id = parts[3]
    index = int(parts[4])
    user_id = callback.from_user.id

    product = await api_client.get_product_by_id(product_id)
    products = await api_client.get_products_by_category(category_id)

    if not product or not products:
        await callback.answer("Товар или категория не найдены.", show_alert=True)
        return

    message_text = await format_product_message(product, user_id, index, len(products))
    is_fav = await api_client.check_favorite(user_id, product_id)

    await callback.message.delete()

    photo_url = get_valid_photo_url(product)
    if photo_url:
        optimized_photo = await get_optimized_photo(photo_url)
        if optimized_photo:
            await callback.message.answer_photo(
                photo=optimized_photo,
                caption=message_text,
                reply_markup=get_product_keyboard(
                    product, category_id, index, len(products), is_fav
                ),
            )
        else:
            # Fallback if optimization fails
            await callback.message.answer(
                f"📷 Не удалось загрузить фото\n\n{message_text}",
                reply_markup=get_product_keyboard(
                    product, category_id, index, len(products), is_fav
                ),
            )
    else:
        # Fallback: отправить текстовое сообщение, если нет фото
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=get_product_keyboard(
                product,
                category_id,
                index,
                len(products),
                is_fav
            )
        )
    await callback.answer()


@router.callback_query(F.data.startswith("tryon:"))
async def try_on_coming_soon(callback: CallbackQuery):
    """Заглушка для функции примерки"""
    text = """👗 Примерка одежды

Эта функция скоро будет доступна! 🚀

Ты сможешь:
• Загрузить свое фото
• Увидеть, как на тебе будет смотреться выбранный товар
• Сохранить результат примерки

Следи за обновлениями! ✨"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="close_tryon")]
    ])

    await callback.message.answer(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("product:"))
async def view_product(callback: CallbackQuery):
    """Просмотр товара (без навигации)"""
    product_id = callback.data.split(":")[1]
    user_id = callback.from_user.id

    product = await api_client.get_product_by_id(product_id)
    if not product:
        await callback.answer("❌ Товар не найден.", show_alert=True)
        return

    is_fav = await api_client.check_favorite(user_id, product_id)

    # Формируем сообщение без навигации
    message_text = f"👗 {product['name']}\n\n{product['description']}\n\n"
    if product.get('available_sizes'):
        message_text += f"📏 Доступные размеры: {product['available_sizes']}"

    # Клавиатура без навигации
    keyboard = []

    # Кнопки магазинов
    shop_buttons = []
    if product.get('wb_link'):
        shop_buttons.append(InlineKeyboardButton(text="🛒 WB", url=product['wb_link']))
    if product.get('ozon_url'):
        shop_buttons.append(InlineKeyboardButton(text="🛒 Ozon", url=product['ozon_url']))
    if shop_buttons:
        keyboard.append(shop_buttons)

    # Кнопка избранного
    if is_fav:
        keyboard.append([InlineKeyboardButton(text="💔 Убрать из избранного", callback_data=f"fav:remove:{product_id}")])
    else:
        keyboard.append([InlineKeyboardButton(text="💖 В избранное", callback_data=f"fav:add:{product_id}")])

    # Кнопка примерки
    keyboard.append([InlineKeyboardButton(text="👗 Примерить", callback_data=f"tryon:start:{product_id}")])

    # Кнопка назад
    keyboard.append([InlineKeyboardButton(text="◀️ В каталог", callback_data="catalog")])

    await callback.message.delete()

    photo_url = get_valid_photo_url(product)
    if photo_url:
        optimized_photo = await get_optimized_photo(photo_url)
        if optimized_photo:
            await callback.message.answer_photo(
                photo=optimized_photo,
                caption=message_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
        else:
            await callback.message.answer(
                f"📷 Не удалось загрузить фото\n\n{message_text}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
            )
    else:
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await callback.answer()


@router.callback_query(F.data == "close_tryon")
async def close_tryon_message(callback: CallbackQuery):
    """Закрыть сообщение о примерке"""
    await callback.message.delete()
    await callback.answer()
