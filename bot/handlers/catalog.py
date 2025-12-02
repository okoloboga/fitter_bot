"""
Обработчики каталога товаров
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto, URLInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from bot.keyboards.catalog import (
    get_categories_keyboard,
    get_product_keyboard,
    get_back_to_product_keyboard
)
from bot.utils.api_client import api_client

router = Router()


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

    message_text = f"""🧥 {product.get('name', 'Без названия')}

{product.get('description', '')}

Размеры: {product.get('available_sizes', 'Нет данных')}{size_recommendation}

Товар {current_index + 1} из {total_count}"""

    return message_text


@router.callback_query(F.data == "back:categories")
async def back_to_categories(callback: CallbackQuery):
    """Возврат к списку категорий"""
    categories = await api_client.get_categories()
    keyboard = get_categories_keyboard(categories)
    await callback.message.edit_text(
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

    await callback.message.answer_photo(
        photo=URLInputFile(product['collage_url']),
        caption=message_text,
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

    try:
        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=URLInputFile(product['collage_url']),
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
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=URLInputFile(product['collage_url']),
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

    media = [
        InputMediaPhoto(media=URLInputFile(product['photo_1_url'])),
        InputMediaPhoto(media=URLInputFile(product['photo_2_url'])),
        InputMediaPhoto(media=URLInputFile(product['photo_3_url'])),
        InputMediaPhoto(media=URLInputFile(product['photo_4_url'])),
    ]

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
    await callback.message.answer_photo(
        photo=URLInputFile(product['collage_url']),
        caption=message_text,
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


@router.callback_query(F.data == "close_tryon")
async def close_tryon_message(callback: CallbackQuery):
    """Закрыть сообщение о примерке"""
    await callback.message.delete()
    await callback.answer()
