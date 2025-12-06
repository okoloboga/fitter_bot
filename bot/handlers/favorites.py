"""
Обработчики раздела избранного
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, URLInputFile, InputMediaPhoto, BufferedInputFile

from bot.keyboards.catalog import get_favorites_product_keyboard, get_go_to_catalog_keyboard
from bot.keyboards.main_menu import get_main_menu
from bot.utils.api_client import api_client
from bot.handlers.catalog import get_valid_photo_url
from bot.utils.image_processor import get_optimized_photo

router = Router()


async def format_favorite_product_message(product: dict, user_id: int, current_index: int, total_count: int):
    """Форматировать сообщение карточки товара в избранном"""
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
            size_recommendation = f"\n\n{recommendation.get('message', '⚠️ Не удалось подобрать размер')}"
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


@router.callback_query(F.data == "favorites")
async def show_favorites(callback: CallbackQuery):
    """Показать избранное"""
    user_id = callback.from_user.id
    favorites = await api_client.get_favorites(user_id)

    if not favorites:
        await callback.message.edit_text(
            "⭐️ Избранное\n\nТвое избранное пока пусто. Добавь понравившиеся товары из каталога! 💫",
            reply_markup=get_go_to_catalog_keyboard()
        )
        await callback.answer()
        return

    # API возвращает список словарей, нам нужен ID
    product_id = favorites[0]['product_id']
    product = await api_client.get_product_by_id(product_id)

    if not product:
        await callback.message.edit_text(
            "⭐️ Избранное\n\nТовар не найден",
            reply_markup=get_main_menu()
        )
        await callback.answer()
        return

    message_text = await format_favorite_product_message(product, user_id, 0, len(favorites))

    await callback.message.delete()

    photo_url = get_valid_photo_url(product)
    if photo_url:
        optimized_photo = await get_optimized_photo(photo_url)
        if optimized_photo:
            await callback.message.answer_photo(
                photo=optimized_photo,
                caption=message_text,
                reply_markup=get_favorites_product_keyboard(product, 0, len(favorites))
            )
        else:
            await callback.message.answer(
                f"📷 Не удалось загрузить фото\n\n{message_text}",
                reply_markup=get_favorites_product_keyboard(product, 0, len(favorites))
            )
    else:
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=get_favorites_product_keyboard(product, 0, len(favorites))
        )
    await callback.answer()


@router.callback_query(F.data.startswith("fav:add:"))
async def add_favorite(callback: CallbackQuery):
    """Добавить товар в избранное"""
    product_id = callback.data.split(":")[2]
    user_id = callback.from_user.id

    await api_client.add_to_favorites(user_id, product_id)

    await callback.answer("Товар добавлен в избранное ⭐️")

    if callback.message.reply_markup:
        try:
            new_keyboard = callback.message.reply_markup.inline_keyboard.copy()
            new_keyboard[0] = [
                type(new_keyboard[0][0])(
                    text="❌ Убрать из избранного",
                    callback_data=f"fav:remove:{product_id}"
                )
            ]
            from aiogram.types import InlineKeyboardMarkup
            await callback.message.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard)
            )
        except:
            pass


@router.callback_query(F.data.startswith("fav:remove:"))
async def remove_favorite(callback: CallbackQuery):
    """Удалить товар из избранного"""
    product_id = callback.data.split(":")[2]
    user_id = callback.from_user.id

    await api_client.remove_from_favorites(user_id, product_id)

    await callback.answer("Товар удален из избранного")

    if callback.message.reply_markup:
        try:
            new_keyboard = callback.message.reply_markup.inline_keyboard.copy()
            is_in_favorites_view = any(
                "nav_fav" in str(button.callback_data)
                for row in new_keyboard
                for button in row
                if hasattr(button, 'callback_data')
            )

            if is_in_favorites_view:
                favorites = await api_client.get_favorites(user_id)
                if not favorites:
                    await callback.message.delete()
                    await callback.message.answer(
                        "⭐️ Избранное\n\nТвое избранное пусто. Добавь понравившиеся товары из каталога! 💫",
                        reply_markup=get_go_to_catalog_keyboard()
                    )
                else:
                    product_id = favorites[0]['product_id']
                    product = await api_client.get_product_by_id(product_id)
                    message_text = await format_favorite_product_message(product, user_id, 0, len(favorites))
                    
                    photo_url = get_valid_photo_url(product)
                    if not photo_url:
                        await callback.message.delete()
                        await callback.message.answer(
                            f"📷 Фото недоступно\n\n{message_text}",
                            reply_markup=get_favorites_product_keyboard(product, 0, len(favorites))
                        )
                        return

                    optimized_photo = await get_optimized_photo(photo_url)
                    if not optimized_photo:
                        await callback.answer("Не удалось загрузить фото товара", show_alert=True)
                        return

                    await callback.message.edit_media(
                        media=InputMediaPhoto(
                            media=optimized_photo,
                            caption=message_text
                        ),
                        reply_markup=get_favorites_product_keyboard(product, 0, len(favorites))
                    )
            else:
                new_keyboard[0] = [
                    type(new_keyboard[0][0])(
                        text="⭐️ В избранное",
                        callback_data=f"fav:add:{product_id}"
                    )
                ]
                from aiogram.types import InlineKeyboardMarkup
                await callback.message.edit_reply_markup(
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=new_keyboard)
                )
        except Exception as e:
            print(f"Error updating keyboard: {e}")
            pass


@router.callback_query(F.data.startswith("nav_fav:"))
async def navigate_favorites(callback: CallbackQuery):
    """Навигация по избранному"""
    parts = callback.data.split(":")
    current_index = int(parts[1])
    action = parts[2]

    user_id = callback.from_user.id
    favorites = await api_client.get_favorites(user_id)

    if not favorites:
        await callback.answer("Избранное пусто", show_alert=True)
        return

    if action == "next":
        new_index = (current_index + 1) % len(favorites)
    else:  # prev
        new_index = (current_index - 1 + len(favorites)) % len(favorites)

    product_id = favorites[new_index]['product_id']
    product = await api_client.get_product_by_id(product_id)

    if not product:
        await callback.answer("Товар не найден", show_alert=True)
        return

    message_text = await format_favorite_product_message(product, user_id, new_index, len(favorites))
    photo_url = get_valid_photo_url(product)

    if not photo_url:
        # If no photo, we can't use edit_media, so we delete and send a new message
        await callback.message.delete()
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=get_favorites_product_keyboard(product, new_index, len(favorites))
        )
        await callback.answer()
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
            reply_markup=get_favorites_product_keyboard(product, new_index, len(favorites))
        )
    except:
        await callback.message.delete()
        await callback.message.answer_photo(
            photo=optimized_photo,
            caption=message_text,
            reply_markup=get_favorites_product_keyboard(product, new_index, len(favorites))
        )
    await callback.answer()


@router.callback_query(F.data.startswith("photos_fav:"))
async def show_favorite_photos(callback: CallbackQuery):
    """Показать все фото товара из избранного"""
    parts = callback.data.split(":")
    product_id = parts[1]
    index = int(parts[2])

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
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="◀️ Вернуться к товару",
            callback_data=f"back_fav:{product_id}:{index}"
        )]
    ])
    await callback.message.answer(
        "📸 Все фото товара",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_fav:"))
async def back_to_favorite_product(callback: CallbackQuery):
    """Вернуться к товару в избранном"""
    parts = callback.data.split(":")
    product_id = parts[1]
    index = int(parts[2])

    user_id = callback.from_user.id
    favorites = await api_client.get_favorites(user_id)
    product = await api_client.get_product_by_id(product_id)

    message_text = await format_favorite_product_message(product, user_id, index, len(favorites))

    await callback.message.delete()
    
    photo_url = get_valid_photo_url(product)
    if photo_url:
        optimized_photo = await get_optimized_photo(photo_url)
        if optimized_photo:
            await callback.message.answer_photo(
                photo=optimized_photo,
                caption=message_text,
                reply_markup=get_favorites_product_keyboard(product, index, len(favorites))
            )
        else:
            await callback.message.answer(
                f"📷 Не удалось загрузить фото\n\n{message_text}",
                reply_markup=get_favorites_product_keyboard(product, index, len(favorites))
            )
    else:
        await callback.message.answer(
            f"📷 Фото недоступно\n\n{message_text}",
            reply_markup=get_favorites_product_keyboard(product, index, len(favorites))
        )
    await callback.answer()
