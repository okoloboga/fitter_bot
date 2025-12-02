"""
Обработчики административной панели
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot.utils.storage import user_measurements, user_favorites

router = Router()


ADMIN_STATS_TEXT = """📊 Статистика бота

👥 Пользователи:
Всего: 127
Новых за сегодня: 5
Новых за 7 дней: 23
Активных за 7 дней: 89

📐 Параметры:
Указали параметры: {measurements_count}

⭐️ Избранное:
Всего добавлений: {favorites_count}

🔥 ТОП-3 категорий:
1. Куртки оверсайз - 45 просмотров
2. Пальто - 32 просмотра
3. Штаны - 28 просмотров"""


def get_admin_stats_keyboard():
    """Клавиатура для админ-панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
    ])


@router.message(Command("admin_stats"))
async def show_admin_stats(message: Message):
    """Показать статистику (для этапа 0 доступна всем)"""

    # Считаем реальную статистику из хранилища в памяти
    measurements_count = len(user_measurements)

    # Считаем общее количество избранных товаров
    favorites_count = sum(len(favs) for favs in user_favorites.values())

    stats_text = ADMIN_STATS_TEXT.format(
        measurements_count=measurements_count,
        favorites_count=favorites_count
    )

    await message.answer(
        stats_text,
        reply_markup=get_admin_stats_keyboard()
    )


@router.callback_query(F.data == "admin:refresh")
async def refresh_admin_stats(callback: CallbackQuery):
    """Обновить статистику"""

    # Считаем актуальную статистику
    measurements_count = len(user_measurements)
    favorites_count = sum(len(favs) for favs in user_favorites.values())

    stats_text = ADMIN_STATS_TEXT.format(
        measurements_count=measurements_count,
        favorites_count=favorites_count
    )

    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_stats_keyboard()
    )

    await callback.answer("Статистика обновлена")
