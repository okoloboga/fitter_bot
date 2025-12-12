"""
Обработчики онбординга новых пользователей
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from pathlib import Path
import os
from datetime import datetime

from bot.states.onboarding import OnboardingStates
from bot.keyboards.onboarding import get_skip_photo_keyboard, get_start_onboarding_keyboard
from bot.keyboards.main_menu import get_main_menu
from bot.utils.api_client import api_client
from gpt_integration.photo_processing.validator import validate_photo

router = Router()
logger = logging.getLogger(__name__)

STORAGE_PATH = Path(os.getenv("STORAGE_PATH", "storage"))
USER_PHOTOS_PATH = STORAGE_PATH / "user_photos"


ONBOARDING_WELCOME = """Добро пожаловать! 👋

Чтобы я мог подобрать тебе идеальную одежду, мне нужно узнать твой размер.

Это займет всего минуту!"""


ONBOARDING_SIZE_REQUEST = """📏 Укажи свой российский размер

Например: 42-44 или просто 44

Этот параметр обязателен для подбора размеров товаров."""


ONBOARDING_PHOTO_REQUEST = """📸 Загрузи свое фото для примерки!

Требования:
• Фото минимум по пояс
• Хорошее освещение
• Лицо должно быть видно

Можешь пропустить этот шаг и добавить фото позже."""


ONBOARDING_COMPLETE = """Отлично! ✨

Теперь ты можешь:
🛍 Просматривать каталог товаров
📐 Получать рекомендации по размеру
👗 Примерять одежду на свое фото

Давай начнем!"""


async def download_telegram_file(bot, file_id: str, save_path: str) -> bool:
    """Скачать файл из Telegram"""
    try:
        file = await bot.get_file(file_id)
        await bot.download_file(file.file_path, save_path)
        return True
    except Exception as e:
        logger.error(f"Failed to download file: {e}")
        return False


async def get_telegram_file_url(bot, file_id: str) -> str:
    """Получить публичный URL файла из Telegram"""
    try:
        file = await bot.get_file(file_id)
        token = bot.token
        return f"https://api.telegram.org/file/bot{token}/{file.file_path}"
    except Exception as e:
        logger.error(f"Failed to get file URL: {e}")
        return None


def compress_image(image_path: str, max_size_mb: int = 10):
    """Сжать изображение если оно больше max_size_mb"""
    from PIL import Image
    import io

    if not os.path.exists(image_path):
        return
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


# === Начало онбординга ===

async def start_onboarding(message: Message, state: FSMContext):
    """Запуск процесса онбординга"""
    await message.answer(
        ONBOARDING_WELCOME,
        reply_markup=get_start_onboarding_keyboard()
    )


@router.callback_query(F.data == "onboarding:start")
async def onboarding_start_handler(callback: CallbackQuery, state: FSMContext):
    """Начало онбординга - запрос российского размера"""
    await state.set_state(OnboardingStates.waiting_russian_size)
    await callback.message.edit_text(ONBOARDING_SIZE_REQUEST)
    await callback.answer()


# === Ввод российского размера (обязательно) ===

@router.message(OnboardingStates.waiting_russian_size)
async def russian_size_received(message: Message, state: FSMContext):
    """Получен российский размер"""
    if not message.text:
        await message.answer(
            "❌ Пожалуйста, введи свой размер текстом (например: 42-44 или 44)",
        )
        return

    russian_size = message.text.strip()

    # Валидация размера
    if not russian_size or len(russian_size) > 20:
        await message.answer(
            "❌ Пожалуйста, введи корректный размер (например: 42-44 или 44)",
        )
        return

    user_id = message.from_user.id

    # Сохраняем российский размер через API
    result = await api_client.save_measurements(user_id, russian_size=russian_size)

    if not result:
        await message.answer("❌ Ошибка сохранения размера. Попробуй еще раз.")
        return

    # Переходим к запросу фото
    await state.set_state(OnboardingStates.waiting_photo)
    await message.answer(
        f"✅ Отлично! Размер {russian_size} сохранен.\n\n{ONBOARDING_PHOTO_REQUEST}",
        reply_markup=get_skip_photo_keyboard()
    )


# === Загрузка фото (опционально) ===

@router.message(OnboardingStates.waiting_photo, F.photo)
async def onboarding_photo_received(message: Message, state: FSMContext):
    """Получено фото во время онбординга"""
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

        # Валидация через ChatGPT
        validation_result = await validate_photo(file_url)
        if not validation_result.get("valid"):
            reason = validation_result.get("description", "Фото не подходит для примерки")
            await status_msg.edit_text(
                f"❌ {reason}\n\nМожешь попробовать загрузить другое фото или пропустить этот шаг.",
                reply_markup=get_skip_photo_keyboard()
            )
            if file_path.exists():
                file_path.unlink()
            return

        # Сохраняем фото в БД
        upload_result = await api_client.upload_photo(tg_id, photo.file_id, str(file_path), True)
        if not upload_result or not upload_result.get("success"):
            await status_msg.edit_text("❌ Ошибка сохранения фото")
            return

        await status_msg.edit_text("✅ Фото принято!")

        # Завершаем онбординг
        await finish_onboarding(message, state)

    except Exception as e:
        logger.error(f"Failed to process onboarding photo: {e}", exc_info=True)
        await status_msg.edit_text("❌ Ошибка обработки фото. Попробуй еще раз")


@router.message(OnboardingStates.waiting_photo, ~F.photo)
async def onboarding_invalid_photo(message: Message):
    """Получено не фото во время ожидания фото"""
    await message.answer(
        "Это не похоже на фото. Пожалуйста, отправь изображение или пропусти этот шаг.",
        reply_markup=get_skip_photo_keyboard()
    )


@router.callback_query(F.data == "onboarding:skip_photo", OnboardingStates.waiting_photo)
async def skip_photo(callback: CallbackQuery, state: FSMContext):
    """Пропуск загрузки фото"""
    await callback.message.edit_text("Хорошо, ты сможешь добавить фото позже в разделе '📐 Мои параметры'")
    await callback.answer()
    await finish_onboarding(callback.message, state)


# === Завершение онбординга ===

async def finish_onboarding(message: Message, state: FSMContext):
    """Завершение онбординга и переход в главное меню"""
    await state.clear()

    # Проверяем наличие истории примерок
    has_history = await api_client.has_tryon_history(message.from_user.id)

    await message.answer(
        ONBOARDING_COMPLETE,
        reply_markup=get_main_menu(has_tryon_history=has_history)
    )
