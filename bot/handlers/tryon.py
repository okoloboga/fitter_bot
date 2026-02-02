"""
Обработчики AI-примерки одежды
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramNetworkError, TelegramAPIError
import logging
import os
import asyncio
from datetime import datetime
from pathlib import Path
from PIL import Image
import io
import base64

from bot.keyboards.main_menu import get_main_menu
from bot.states.tryon import TryOnStates
from bot.utils.api_client import api_client
from gpt_integration.photo_processing.validator import validate_photo
from gpt_integration.photo_processing.generator import generate_tryon
from gpt_integration.photo_processing.prompts import TRYON_SINGLE_ITEM, TRYON_FULL_OUTFIT
from bot.services.photo_preloader import photo_preloader

router = Router()
logger = logging.getLogger(__name__)


async def safe_edit_message(message_or_callback, text: str, max_retries: int = 3):
    """
    Безопасное редактирование сообщения с обработкой сетевых ошибок.
    
    Args:
        message_or_callback: Message или CallbackQuery объект
        text: Текст для отправки
        max_retries: Максимальное количество попыток
    """
    if hasattr(message_or_callback, 'edit_text'):
        msg = message_or_callback
    elif hasattr(message_or_callback, 'message'):
        msg = message_or_callback.message
    else:
        logger.warning("Cannot determine message object for safe_edit_message")
        return
    
    for attempt in range(max_retries):
        try:
            await msg.edit_text(text)
            return
        except (TelegramNetworkError, TelegramAPIError) as e:
            if attempt < max_retries - 1:
                logger.warning(f"Network error editing message (attempt {attempt + 1}/{max_retries}): {e}")
                await asyncio.sleep(1)  # Небольшая задержка перед повтором
            else:
                logger.error(f"Failed to edit message after {max_retries} attempts: {e}")
                # Пробуем отправить новое сообщение вместо редактирования
                try:
                    if hasattr(msg, 'answer'):
                        await msg.answer(text)
                    elif hasattr(message_or_callback, 'message') and hasattr(message_or_callback.message, 'answer'):
                        await message_or_callback.message.answer(text)
                except Exception as e2:
                    logger.error(f"Failed to send new message as fallback: {e2}")
        except Exception as e:
            logger.error(f"Unexpected error editing message: {e}", exc_info=True)
            break

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "storage"))
USER_PHOTOS_PATH = STORAGE_PATH / "user_photos"
TRYON_RESULTS_PATH = STORAGE_PATH / "try_on_results"


# === Вспомогательные функции ===

async def download_telegram_file(bot, file_id: str, save_path: str) -> bool:
    """Скачать файл из Telegram"""
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, save_path)
        return True
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        return False


def compress_image(image_path: str, max_size_mb: int = 10):
    """Сжать изображение если оно больше max_size_mb"""
    if not os.path.exists(image_path): return
    file_size_mb = os.path.getsize(image_path) / (1024 * 1024)

    if file_size_mb <= max_size_mb:
        return

    try:
        img = Image.open(image_path)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')

        quality = 85
        while quality > 20:
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=quality, optimize=True)
            if len(output.getvalue()) / (1024 * 1024) <= max_size_mb:
                with open(image_path, 'wb') as f:
                    f.write(output.getvalue())
                logger.info(f"Compressed image to quality {quality}")
                return
            quality -= 10
        logger.warning("Could not compress image enough")
    except Exception as e:
        logger.error(f"Failed to compress image: {e}")


async def get_telegram_file_url(bot, file_id: str) -> str:
    """Получить публичный URL файла из Telegram"""
    try:
        file = await bot.get_file(file_id)
        token = bot.token
        return f"https://api.telegram.org/file/bot{token}/{file.file_path}"
    except Exception as e:
        logger.error(f"Failed to get file URL: {e}")
        return None


def get_consent_keyboard():
    """Клавиатура согласия на обработку фото"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Согласен", callback_data="tryon:consent:yes")],
        [InlineKeyboardButton(text="❌ Отказаться", callback_data="tryon:consent:no")]
    ])


def get_photo_selection_keyboard(photos: list):
    """Клавиатура выбора фото"""
    keyboard = []
    for i, photo in enumerate(photos):
        keyboard.append([
            InlineKeyboardButton(
                text=f"📸 Фото {i+1} ({datetime.fromisoformat(photo['uploaded_at']).strftime('%d.%m.%Y')})",
                callback_data=f"tryon:select_photo:{photo['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="📤 Загрузить новое фото", callback_data="tryon:upload_new")])
    keyboard.append([InlineKeyboardButton(text="◀️ Отмена", callback_data="tryon:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_model_selection_keyboard():
    """Клавиатура выбора модели генерации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚡️ Быстрая (~1-2 мин)", callback_data="tryon:model:fast")],
        [InlineKeyboardButton(text="👑 Качественная (~3-4 мин)", callback_data="tryon:model:pro")],
        [InlineKeyboardButton(text="🚀 GPT Image 1.5 (~3-4 мин)", callback_data="tryon:model:gpt-image-1.5")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="tryon:cancel")]
    ])


def get_tryon_mode_keyboard():
    """Клавиатура выбора режима примерки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👕 Только этот товар", callback_data="tryon:mode:single_item")],
        [InlineKeyboardButton(text="👗 Весь образ с фото", callback_data="tryon:mode:full_outfit")],
        [InlineKeyboardButton(text="◀️ Отмена", callback_data="tryon:cancel")]
    ])


def get_tryon_result_keyboard(tryon_id: int, product_id: str, wb_link: str, ozon_url: str = None,
                              source: str = 'catalog', category_id: str = '', index: int = 0):
    """Клавиатура после успешной примерки"""
    keyboard = []

    # Кнопки магазинов в одну строку если есть обе ссылки
    shop_buttons = []
    if wb_link:
        shop_buttons.append(InlineKeyboardButton(text="Wildberries", url=wb_link))
    if ozon_url:
        shop_buttons.append(InlineKeyboardButton(text="Ozon", url=ozon_url))

    if shop_buttons:
        if len(shop_buttons) == 2:
            keyboard.append(shop_buttons)
        else:
            keyboard.append([shop_buttons[0]])

    # Формируем коллбэк для возврата
    if source == 'catalog':
        back_callback = f"back:product:{product_id}:{category_id}:{index}"
    elif source == 'favorites':
        back_callback = f"back_fav:{product_id}:{index}"
    else:
        # Фоллбэк на старое поведение, если источник неизвестен
        back_callback = f"product:{product_id}"
        
    retry_callback = f"tryon:retry:{source}:{product_id}:{category_id}:{index}"

    keyboard.extend([
        [InlineKeyboardButton(text="💾 Сохранить результат", callback_data=f"tryon:save_result:{tryon_id}")],
        [InlineKeyboardButton(text="🔄 Другое фото", callback_data=retry_callback)],
        [InlineKeyboardButton(text="◀️ К товару", callback_data=back_callback)]
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_my_photos_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Загрузить фото", callback_data="tryon:upload_new")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="measurements_menu")]
    ])


def get_photo_manage_keyboard(photo_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"tryon:delete_photo:{photo_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="my_photos")]
    ])


# === Начало примерки (кнопка "Примерить" в карточке товара) ===

@router.callback_query(F.data.startswith("tryon:start:"))
async def start_tryon(callback: CallbackQuery, state: FSMContext):
    _tryon, _start, source, product_id, category_id, index_str = callback.data.split(":")
    index = int(index_str)
    tg_id = callback.from_user.id
    try:
        product_data = await api_client.get_product_by_id(product_id)
        if not product_data:
            await callback.answer("❌ Товар не найден. Возможно, он был удален.", show_alert=True)
            return

        # Сохраняем базовую информацию о товаре в state
        await state.update_data(
            source=source,
            product_id=product_id,
            category_id=category_id,
            index=index,
            product_name=product_data.get("name"),
            product_category=product_data.get("category", "одежда"),
            wb_link=product_data.get("wb_link"),
            ozon_url=product_data.get("ozon_url"),
        )
        
        # Проверяем лимит примерок
        limit_result = await api_client.check_tryon_limit(tg_id)
        if limit_result and limit_result.get("limit_reached"):
            await callback.answer(f"Ты достиг лимита примерок на сегодня ({limit_result.get('count', 20)}/20). Попробуй завтра! 😊", show_alert=True)
            return

        # Сразу запрашиваем режим примерки
        await state.set_state(TryOnStates.waiting_tryon_mode)
        await callback.message.answer(
            "Выбери режим примерки:\n\n"
            "👕 <b>Только этот товар</b> - на тебе изменится только выбранная вещь, остальная одежда останется твоей\n\n"
            "👗 <b>Весь образ с фото</b> - на тебя примерят всю одежду, которая есть на модели с фото товара",
            reply_markup=get_tryon_mode_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Failed to start try-on: {e}", exc_info=True)
        await callback.answer("❌ Ошибка запуска примерки", show_alert=True)


@router.callback_query(F.data.startswith("tryon:retry:"))
async def retry_tryon(callback: CallbackQuery, state: FSMContext):
    """Повторная примерка с другим фото"""
    _tryon, _retry, source, product_id, category_id, index_str = callback.data.split(":")
    index = int(index_str)
    tg_id = callback.from_user.id
    try:
        product_data = await api_client.get_product_by_id(product_id)
        if not product_data:
            await callback.answer("❌ Товар не найден. Возможно, он был удален.", show_alert=True)
            return

        await state.update_data(
            source=source,
            product_id=product_id,
            category_id=category_id,
            index=index,
            product_name=product_data.get("name"),
            product_category=product_data.get("category", "одежда"),
            wb_link=product_data.get("wb_link"),
            ozon_url=product_data.get("ozon_url"),
        )
        limit_result = await api_client.check_tryon_limit(tg_id)
        if limit_result and limit_result.get("limit_reached"):
            await callback.answer(f"Ты достиг лимита примерок на сегодня ({limit_result.get('count', 20)}/20). Попробуй завтра! 😊", show_alert=True)
            return

        photos_result = await api_client.get_user_photos(tg_id)
        photos = photos_result.get("photos", []) if photos_result else []

        if not photos:
            await state.set_state(TryOnStates.waiting_consent)
            await callback.message.answer(
                "Для работы примерки нам нужно обработать твое фото с помощью AI.\n\n"
                "Мы сохраним фото для повторного использования. "
                "Фото используется только для примерки и не передается третьим лицам.\n\n"
                "Согласен(на)?",
                reply_markup=get_consent_keyboard()
            )
        else:
            await state.set_state(TryOnStates.selecting_photo)
            await callback.message.answer("Выбери фото для примерки:", reply_markup=get_photo_selection_keyboard(photos))
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to retry try-on: {e}", exc_info=True)
        await callback.answer("❌ Ошибка запуска примерки", show_alert=True)


# === Согласие на обработку фото ===

@router.callback_query(F.data == "tryon:consent:yes", TryOnStates.waiting_consent)
async def consent_given(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TryOnStates.waiting_photo)
    await callback.message.edit_text(
        "Чтобы примерить одежду, загрузи свое фото!\n\n"
        "Требования:\n"
        "📸 Фото минимум по пояс\n"
        "💡 Хорошее освещение\n\n"
        "Загрузи фото прямо в чат!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="tryon:cancel")]])
    )
    await callback.answer()


@router.callback_query(F.data == "tryon:consent:no", TryOnStates.waiting_consent)
async def consent_declined(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Хорошо, примерка отменена. Ты всегда можешь вернуться к ней позже!")
    await callback.answer()


# === Загрузка фото ===

@router.callback_query(F.data == "tryon:upload_new")
async def request_photo_upload(callback: CallbackQuery, state: FSMContext):
    await state.set_state(TryOnStates.waiting_photo)
    await callback.message.answer(
        "Загрузи свое фото:\n\n"
        "Требования:\n"
        "📸 Фото минимум по пояс\n"
        "💡 Хорошее освещение\n\n"
        "Отправь фото прямо в чат!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="tryon:cancel")]])
    )
    await callback.answer()


@router.message(TryOnStates.waiting_photo, F.photo)
async def photo_received(message: Message, state: FSMContext):
    tg_id = message.from_user.id
    photo = message.photo[-1]  # Берем самое большое фото
    status_msg = await message.answer("Проверяем фото... 🔍")
    try:
        user_dir = USER_PHOTOS_PATH / str(tg_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = user_dir / f"photo_{timestamp}.jpg"
        if not await download_telegram_file(message.bot, photo.file_id, str(file_path)):
            await status_msg.edit_text("❌ Не удалось скачать фото. Попробуй еще раз")
            return
        compress_image(str(file_path), max_size_mb=10)
        file_url = await get_telegram_file_url(message.bot, photo.file_id)
        if not file_url:
            await status_msg.edit_text("❌ Ошибка обработки фото")
            return
        validation_result = await validate_photo(file_url)
        if not validation_result.get("valid"):
            reason = validation_result.get("description", "Фото не подходит для примерки")
            await status_msg.edit_text(
                f"❌ {reason}\n\nПопробуй загрузить другое фото",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="📸 Загрузить другое фото", callback_data="tryon:upload_new")],
                    [InlineKeyboardButton(text="◀️ Отмена", callback_data="tryon:cancel")]
                ])
            )
            if file_path.exists(): file_path.unlink()
            return

        upload_result = await api_client.upload_photo(tg_id, photo.file_id, str(file_path), True)
        if not upload_result or not upload_result.get("success"):
            await status_msg.edit_text("❌ Ошибка сохранения фото")
            return

        photo_id = upload_result["photo"]["id"]
        await state.update_data(photo_id=photo_id)
        await status_msg.edit_text("✅ Отлично! Фото принято")
        data = await state.get_data()
        if data.get("product_id"):
            # Переходим к выбору модели
            await state.set_state(TryOnStates.selecting_model)
            await message.answer("Отлично! Теперь выбери модель для генерации:", reply_markup=get_model_selection_keyboard())
        else:
            await message.answer("Фото сохранено! Теперь можешь примерять одежду 👗")
            await state.clear()
    except Exception as e:
        logger.error(f"Failed to process photo: {e}", exc_info=True)
        await status_msg.edit_text("❌ Ошибка обработки фото. Попробуй еще раз")


@router.message(TryOnStates.waiting_photo, ~F.photo)
async def invalid_photo_received(message: Message):
    await message.answer(
        "Это не похоже на фото. Пожалуйста, отправь изображение или отмени операцию.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Отмена", callback_data="tryon:cancel")]])
    )


# === Выбор существующего фото и модели ===

@router.callback_query(F.data.startswith("tryon:select_photo:"), TryOnStates.selecting_photo)
async def photo_selected(callback: CallbackQuery, state: FSMContext):
    photo_id = int(callback.data.split(":")[2])
    await state.update_data(photo_id=photo_id)
    # Переходим к выбору модели
    await state.set_state(TryOnStates.selecting_model)
    await callback.message.edit_text("Отлично! Теперь выбери модель для генерации:", reply_markup=get_model_selection_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("tryon:model:"), TryOnStates.selecting_model)
async def model_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора модели - запуск генерации"""
    model_type = callback.data.split(":")[2]
    
    # Маппинг типов моделей на их API названия и отображаемые имена
    # Доступные модели:
    # - fast: gemini-2.5-flash-image (быстрая генерация, ~1-2 мин)
    # - pro: gemini-3-pro-image (качественная генерация, ~3-4 мин)
    # - gpt-image-1.5: GPT Image 1.5 (альтернативная модель, ~X мин)
    # 
    # Можно переопределить названия через переменные окружения:
    # GPT_IMAGE_1_5_MODEL
    model_mapping = {
        "fast": ("gemini-2.5-flash-image", "Быстрая"),
        "pro": ("gemini-3-pro-image", "Качественная"),
        "gpt-image-1.5": (
            # Явно указываем модель gpt-image-1.5 (как в апи-доке CometAPI image-edits).
            # При необходимости можно переопределить через переменную окружения GPT_IMAGE_1_5_MODEL.
            os.getenv("GPT_IMAGE_1_5_MODEL", "gpt-image-1.5"),
            "GPT Image 1.5"
        )
    }
    
    if model_type not in model_mapping:
        await callback.answer("❌ Неизвестная модель", show_alert=True)
        await state.clear()
        return
    
    model, model_name = model_mapping[model_type]

    # Сохраняем выбранную модель в state
    await state.update_data(model=model, model_name=model_name)

    # Получаем все данные из state для запуска генерации
    data = await state.get_data()
    product_id = data.get("product_id")
    photo_id = data.get("photo_id")
    tryon_mode = data.get("tryon_mode")

    if not all([product_id, photo_id, model, tryon_mode]):
        await callback.answer("❌ Ошибка: сессия истекла, начните заново.", show_alert=True)
        await state.clear()
        return

    # Запускаем генерацию
    await callback.answer()
    # Удаляем клавиатуру, чтобы пользователь не нажал ничего лишнего
    await callback.message.edit_reply_markup(reply_markup=None)
    await start_generation(callback.message, state, product_id, photo_id, model, model_name, tryon_mode)


@router.callback_query(F.data.startswith("tryon:mode:"), TryOnStates.waiting_tryon_mode)
async def tryon_mode_selected(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора режима примерки - переход к выбору/загрузке фото"""
    tryon_mode = callback.data.split(":")[2]  # "single_item" или "full_outfit"
    tg_id = callback.from_user.id

    # Сохраняем режим примерки
    await state.update_data(tryon_mode=tryon_mode)

    # Теперь выполняем логику, которая раньше была в start_tryon
    photos_result = await api_client.get_user_photos(tg_id)
    photos = photos_result.get("photos", []) if photos_result else []

    if not photos:
        await state.set_state(TryOnStates.waiting_consent)
        await callback.message.edit_text(
            "Для работы примерки нам нужно обработать твое фото с помощью AI.\n\n"
            "Мы сохраним фото для повторного использования. "
            "Фото используется только для примерки и не передается третьим лицам.\n\n"
            "Согласен(на)?",
            reply_markup=get_consent_keyboard()
        )
    else:
        await state.set_state(TryOnStates.selecting_photo)
        await callback.message.edit_text("Выбери фото для примерки:", reply_markup=get_photo_selection_keyboard(photos))
    
    await callback.answer()


# === Генерация примерки ===

async def start_generation(message: Message, state: FSMContext, product_id: str, photo_id: int, model: str, model_name: str, tryon_mode: str):
    tg_id = message.chat.id
    tryon_create_result = await api_client.create_tryon(tg_id, product_id, photo_id)
    if not tryon_create_result or not tryon_create_result.get("success"):
        error_msg = tryon_create_result.get("message") if tryon_create_result else "Ошибка создания примерки"
        await message.answer(f"❌ {error_msg}")
        await state.clear()
        return

    tryon_id = tryon_create_result["tryon_id"]
    # Маппинг времени генерации для разных моделей
    time_mapping = {
        "gemini-2.5-flash-image": "1-2 минуты",
        "gemini-3-pro-image": "3-4 минуты",
        "gpt-image-1.5": "3-4 минуты"  # TODO: Уточнить после тестирования
    }
    time_estimate = time_mapping.get(model, "2-3 минуты")
    status_msg = await message.answer(f"🎨 Создаем твою примерку с помощью {model_name} модели...\nЭто займет около {time_estimate} ⏳")

    try:
        fsm_data = await state.get_data()
        product_name = fsm_data.get("product_name")
        product_category = fsm_data.get("product_category", "одежда")
        wb_link = fsm_data.get("wb_link", "https://www.wildberries.ru/")
        ozon_url = fsm_data.get("ozon_url")
        product_id_fsm = fsm_data.get("product_id")
        source = fsm_data.get("source", "catalog")

        # Get local path for product photo
        product_photo_path = photo_preloader.get_photo_path(product_id_fsm, '1') # Assuming '1' is the photo_type for the main product photo
        product_photo_sources = []
        if product_photo_path and product_photo_path.exists():
            product_photo_sources.append(str(product_photo_path))

        # Проверка наличия фото товара для примерки
        if not product_photo_sources:
            await safe_edit_message(status_msg, "❌ К сожалению, для этого товара нельзя сделать примерку, так как отсутствует эталонное фото в локальном хранилище.")
            await api_client.update_tryon(tryon_id, status="failed")
            await state.clear()
            return

        category_id = fsm_data.get("category_id", "")
        index = fsm_data.get("index", 0)

        if not product_name:
            await safe_edit_message(status_msg, "❌ Ошибка: данные о товаре (название) не найдены в сессии.")
            await api_client.update_tryon(tryon_id, status="failed")
            await state.clear()
            return

        photos_result = await api_client.get_user_photos(tg_id)
        user_photo = next((p for p in photos_result.get("photos", []) if p["id"] == photo_id), None) if photos_result else None
        if not user_photo:
            await safe_edit_message(status_msg, "❌ Фото не найдено")
            await api_client.update_tryon(tryon_id, status="failed")
            await state.clear()
            return

        # Use local file path for user photo
        user_photo_source = user_photo["file_path"]
        api_key = os.getenv("IMAGE_GEN_API_KEY") or os.getenv("COMET_API_KEY")
        base_url = os.getenv("IMAGE_GEN_BASE_URL", "https://api.cometapi.com")

        # Determine the prompt for logging
        if tryon_mode == "single_item":
            prompt_str = TRYON_SINGLE_ITEM.format(category=product_category)
        elif tryon_mode == "full_outfit":
            prompt_str = TRYON_FULL_OUTFIT
        else:
            prompt_str = f"Unsupported tryon_mode: '{tryon_mode}'. This should not happen due to prior validation."

        logger.info(f"""Generating try-on with:
    Image 1 (User Photo): {user_photo_source}
    Images 2-3 (Product Photos): {product_photo_sources}
    Try-on Mode: {tryon_mode}
    Prompt: {prompt_str}""")

        generation_result = await generate_tryon(
            user_photo_source=user_photo_source,
            product_photo_sources=product_photo_sources,
            api_key=api_key,
            base_url=base_url,
            model=model,
            tryon_mode=tryon_mode,
            item_name=product_name,
            category=product_category
        )
        if not generation_result.get("success"):
            error_msg = generation_result.get("error", {}).get("message", "Не удалось создать примерку")
            await safe_edit_message(status_msg, f"❌ {error_msg}")
            await api_client.update_tryon(tryon_id, status="failed")
            await state.clear()
            return

        result_data_uri = generation_result["result"]["photo_url"]
        generation_time = generation_result["result"]["processing_time"]
        base64_data = result_data_uri.split(",")[1]
        image_data = base64.b64decode(base64_data)
        results_dir = TRYON_RESULTS_PATH / str(tg_id)
        results_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_path = results_dir / f"tryon_{product_id}_{timestamp}.png"
        with open(result_path, "wb") as f: f.write(image_data)

        # Сохраняем абсолютный путь в БД
        absolute_path = str(result_path.resolve())
        logger.info(f"Saving try-on result to: {absolute_path}")
        await api_client.update_tryon(tryon_id, "success", absolute_path, generation_time)

        result_photo = FSInputFile(result_path)
        await message.answer_photo(
            photo=result_photo,
            caption=f"Вот как на тебе будет смотреться {product_name}! 💫",
            reply_markup=get_tryon_result_keyboard(tryon_id, product_id, wb_link, ozon_url, source, category_id, index)
        )
        await status_msg.delete()
    except Exception as e:
        logger.error(f"Failed to generate try-on: {e}", exc_info=True)
        await safe_edit_message(status_msg, "❌ Ошибка генерации примерки")
        try:
            await api_client.update_tryon(tryon_id, status="failed")
        except Exception as e2:
            logger.error(f"Failed to update tryon status: {e2}")
    finally:
        await state.clear()


# === Сохранение результата и История ===

@router.callback_query(F.data.startswith("tryon:save_result:"))
async def save_tryon_result(callback: CallbackQuery, state: FSMContext):
    _tryon, _save_result, tryon_id_str = callback.data.split(":")
    tryon_id = int(tryon_id_str)
    tg_id = callback.from_user.id

    try:
        # Получаем всю историю примерок пользователя
        history_result = await api_client.get_tryon_history(tg_id)
        history = history_result.get("history", []) if history_result else []

        # Ищем конкретную примерку по tryon_id
        current_tryon = next((t for t in history if t["id"] == tryon_id), None)

        if current_tryon:
            result_path = current_tryon.get("result_file_path")

            logger.info(f"Trying to send result file for tryon_id {tryon_id}: {result_path}")

            # Если путь относительный, преобразуем в абсолютный
            if result_path and not os.path.isabs(result_path):
                result_path = str((Path.cwd() / result_path).resolve())
                logger.info(f"Converted to absolute path: {result_path}")

            if result_path and os.path.exists(result_path):
                result_file = FSInputFile(result_path)
                await callback.message.answer_document(document=result_file, caption="Результат примерки сохранен! 📥")
                await callback.answer("✅ Отправлено!")
            else:
                logger.error(f"Result file not found for tryon_id {tryon_id}. Path: {result_path}")
                await callback.answer("❌ Файл результата не найден.", show_alert=True)
        else:
            logger.warning(f"Try-on record with ID {tryon_id} not found in history for user {tg_id}.")
            await callback.answer("❌ Не удалось найти результат примерки.", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to save try-on result for user {tg_id}, tryon_id {tryon_id}: {e}", exc_info=True)
        await callback.answer("❌ Произошла ошибка при сохранении результата.", show_alert=True)


@router.callback_query(F.data == "my_photos")
async def show_my_photos(callback: CallbackQuery):
    tg_id = callback.from_user.id
    try:
        photos_result = await api_client.get_user_photos(tg_id)
        photos = photos_result.get("photos", []) if photos_result else []
        if not photos:
            text = "📸 Мои фото\n\nУ тебя пока нет сохраненных фото"
            keyboard = get_my_photos_keyboard()
        else:
            text = f"📸 Мои фото ({len(photos)}/3)\n\nНажми на фото, чтобы удалить его."
            keyboard_list = []
            for i, photo in enumerate(photos):
                keyboard_list.append([InlineKeyboardButton(
                    text=f"Фото {i+1} ({datetime.fromisoformat(photo['uploaded_at']).strftime('%d.%m.%Y')})",
                    callback_data=f"tryon:view_photo:{photo['id']}"
                )])
            keyboard_list.append([InlineKeyboardButton(text="📤 Загрузить новое", callback_data="tryon:upload_new")])
            keyboard_list.append([InlineKeyboardButton(text="◀️ Назад", callback_data="measurements_menu")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_list)

        # Пытаемся отредактировать, если не получится - удаляем и отправляем новое
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception as edit_error:
            # Если не можем отредактировать (например, было фото), удаляем и отправляем новое
            logger.debug(f"Could not edit message, deleting and sending new: {edit_error}")
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard)

        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to show photos: {e}", exc_info=True)
        await callback.answer("❌ Ошибка загрузки фото", show_alert=True)


@router.callback_query(F.data.startswith("tryon:view_photo:"))
async def view_photo(callback: CallbackQuery):
    photo_id = int(callback.data.split(":")[2])
    tg_id = callback.from_user.id
    try:
        photos_result = await api_client.get_user_photos(tg_id)
        photo = next((p for p in photos_result.get("photos", []) if p["id"] == photo_id), None) if photos_result else None
        if not photo:
            await callback.answer("❌ Фото не найдено", show_alert=True)
            return
        await callback.message.answer_photo(
            photo=photo["file_id"],
            caption=f"📸 Загружено: {datetime.fromisoformat(photo['uploaded_at']).strftime('%d.%m.%Y')}",
            reply_markup=get_photo_manage_keyboard(photo_id)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to view photo: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("tryon:delete_photo:"))
async def delete_photo_handler(callback: CallbackQuery):
    photo_id = int(callback.data.split(":")[2])
    try:
        success = await api_client.delete_photo(photo_id)
        if success:
            await callback.message.delete()
            await callback.answer("✅ Фото удалено")
        else:
            await callback.answer("❌ Ошибка удаления", show_alert=True)
    except Exception as e:
        logger.error(f"Failed to delete photo: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "tryon_history")
async def show_tryon_history(callback: CallbackQuery, state: FSMContext):
    tg_id = callback.from_user.id
    try:
        history_result = await api_client.get_tryon_history(tg_id)
        history = history_result.get("history", []) if history_result else []
        if not history:
            await callback.message.edit_text(
                "📜 История примерок\n\nУ тебя пока нет примерок. Попробуй примерить что-нибудь из каталога! 👗",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛍 Перейти в каталог", callback_data="catalog")],
                    [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
                ])
            )
        else:
            await state.update_data(history=history, history_index=0)
            await show_tryon_card(callback.message, history, 0, edit=True)
        await callback.answer()
    except Exception as e:
        logger.error(f"Failed to show history: {e}", exc_info=True)
        await callback.answer("❌ Ошибка загрузки истории", show_alert=True)


async def show_tryon_card(message: Message, history: list, index: int, edit: bool = False):
    if not (0 <= index < len(history)): return
    tryon = history[index]
    result_path = tryon.get("result_file_path")

    if not result_path or not os.path.exists(result_path):
        text = f"❌ Файл примерки не найден\n\nПримерка {index+1} из {len(history)}"
        keyboard = get_history_navigation_keyboard(index, len(history), tryon)
        if edit: await message.edit_text(text, reply_markup=keyboard)
        else: await message.answer(text, reply_markup=keyboard)
        return

    product_id = tryon["product_id"]
    product_data = await api_client.get_product_by_id(product_id)
    product_name = product_data["name"] if product_data else product_id
    result_photo = FSInputFile(result_path)
    caption = f"👗 {product_name}\n\n📅 {datetime.fromisoformat(tryon['created_at']).strftime('%d.%m.%Y')}\n\nПримерка {index+1} из {len(history)}"
    keyboard = get_history_navigation_keyboard(index, len(history), tryon)
    if edit: await message.delete()
    await message.answer_photo(photo=result_photo, caption=caption, reply_markup=keyboard)


def get_history_navigation_keyboard(index: int, total: int, tryon: dict):
    buttons = []
    
    # Кнопки магазинов
    shop_buttons = []
    wb_link = tryon.get('wb_link')
    ozon_url = tryon.get('ozon_url')
    if wb_link:
        shop_buttons.append(InlineKeyboardButton(text="Wildberries", url=wb_link))
    if ozon_url:
        shop_buttons.append(InlineKeyboardButton(text="Ozon", url=ozon_url))
    
    if shop_buttons:
        buttons.append(shop_buttons)

    # Навигация
    nav_row = []
    if index > 0: nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"tryon_hist:prev:{index}"))
    nav_row.append(InlineKeyboardButton(text=f"({index+1}/{total})", callback_data="noop"))
    if index < total - 1: nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"tryon_hist:next:{index}"))
    
    if nav_row:
        buttons.append(nav_row)

    # Управление и выход
    tryon_id = tryon["id"]
    buttons.extend([
        [InlineKeyboardButton(text="💾 Скачать", callback_data=f"tryon_hist:download:{tryon_id}"),
         InlineKeyboardButton(text="🗑 Удалить", callback_data=f"tryon_hist:delete:{tryon_id}")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data.startswith("tryon_hist:"))
async def handle_history_navigation(callback: CallbackQuery, state: FSMContext):
    action, *params = callback.data.split(":")[1:]
    data = await state.get_data()
    history = data.get("history", [])
    current_index = data.get("history_index", 0)

    if action in ["prev", "next"]:
        new_index = current_index + (-1 if action == "prev" else 1)
        await state.update_data(history_index=new_index)
        await show_tryon_card(callback.message, history, new_index, edit=True)
    elif action == "download":
        tryon_id = int(params[0])
        tryon = next((t for t in history if t["id"] == tryon_id), None)
        if tryon and os.path.exists(tryon["result_file_path"]):
            await callback.message.answer_document(document=FSInputFile(tryon["result_file_path"]), caption="📥 Результат примерки")
            await callback.answer("✅ Отправлено!")
        else:
            await callback.answer("❌ Файл не найден", show_alert=True)
    elif action == "delete":
        tryon_id = int(params[0])
        if await api_client.delete_tryon(tryon_id):
            await callback.answer("✅ Примерка удалена")
            history = [t for t in history if t["id"] != tryon_id]
            if not history:
                await callback.message.delete()
                await callback.message.answer("История примерок пуста", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
                ]))
            else:
                new_index = min(current_index, len(history) - 1)
                await state.update_data(history=history, history_index=new_index)
                await show_tryon_card(callback.message, history, new_index, edit=True)
        else:
            await callback.answer("❌ Ошибка удаления", show_alert=True)


# === Отмена ===

@router.callback_query(F.data == "tryon:cancel")
async def cancel_tryon(callback: CallbackQuery, state: FSMContext):
    """Отмена примерки"""
    await state.clear()
    # Check if user has history to show the correct main menu
    has_history = await api_client.has_tryon_history(callback.from_user.id)
    await callback.message.edit_text(
        "Примерка отменена. Вы в главном меню.",
        reply_markup=get_main_menu(has_tryon_history=has_history)
    )
    await callback.answer()