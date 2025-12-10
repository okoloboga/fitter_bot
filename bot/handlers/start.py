"""
Обработчики команды /start и главного меню
"""
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.keyboards.main_menu import get_main_menu
from bot.keyboards.catalog import get_categories_keyboard
from bot.utils.api_client import api_client

router = Router()


WELCOME_TEXT = """Привет! 👋

Я помогу тебе подобрать идеальную одежду!

Что я умею:
🛍 Показать каталог товаров
📐 Подобрать размер по твоим параметрам
👗 Примерить одежду на твое фото (скоро!)
⭐️ Сохранить понравившиеся товары

Давай начнем!"""

WELCOME_BACK_TEXT = "С возвращением! 😊"

ABOUT_TEXT = """ℹ️ О боте

Этот бот создан для удобного выбора одежды!

🛍 Каталог
Просматривай товары по категориям, листай карточки с фото и описаниями

📐 Подбор размера
Укажи свои параметры один раз, и мы будем рекомендовать подходящий размер для каждого товара

⭐️ Избранное
Сохраняй понравившиеся товары, чтобы вернуться к ним позже

👗 Примерка (скоро!)
Загрузи свое фото и посмотри, как на тебе будет смотреться выбранная одежда

Приятного шопинга! ✨"""


@router.message(Command("start"), StateFilter("*"))
async def cmd_start(message: Message, state: FSMContext):
    """Обработчик команды /start - работает из любого состояния"""
    # Сбрасываем любое активное состояние FSM
    await state.clear()

    # Регистрируем или обновляем пользователя
    await api_client.register_user(
        tg_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name
    )

    # Проверяем наличие истории примерок
    has_history = await api_client.has_tryon_history(message.from_user.id)

    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu(has_tryon_history=has_history)
    )


@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    """Показать каталог товаров"""
    categories = await api_client.get_categories()

    if not categories:
        await callback.message.edit_text(
            "😔 К сожалению, сейчас нет доступных категорий товаров.\n\nПопробуйте зайти позже!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
            ])
        )
        await callback.answer()
        return

    keyboard = get_categories_keyboard(categories)
    await callback.message.edit_text(
        "🛍 Каталог\n\nВыбери категорию:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "about")
async def show_about(callback: CallbackQuery):
    """Показать информацию о боте"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
    ])
    await callback.message.edit_text(
        ABOUT_TEXT,
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    # Проверяем наличие истории примерок
    has_history = await api_client.has_tryon_history(callback.from_user.id)

    # Удаляем предыдущее сообщение и отправляем новое
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        WELCOME_BACK_TEXT,
        reply_markup=get_main_menu(has_tryon_history=has_history)
    )

    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery):
    """Пустой callback для счетчика пагинации"""
    await callback.answer()


@router.message()
async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    import logging
    logger = logging.getLogger(__name__)

    # Логируем что пришло
    logger.info(f"Unknown message received: content_type={message.content_type}, "
                f"has_photo={message.photo is not None}, "
                f"text={message.text if message.text else 'None'}")

    # Если это фото - даем подсказку
    if message.photo:
        await message.answer(
            "Чтобы примерить одежду:\n"
            "1. Перейди в каталог 🛍\n"
            "2. Выбери товар\n"
            "3. Нажми кнопку '👗 Примерить'\n"
            "4. Загрузи свое фото"
        )
        return

    # Проверяем наличие истории примерок
    has_history = await api_client.has_tryon_history(message.from_user.id)

    await message.answer(
        "Я не понял эту команду 😅\n\nВоспользуйся меню ниже или введи /start для перезапуска бота",
        reply_markup=get_main_menu(has_tryon_history=has_history)
    )
