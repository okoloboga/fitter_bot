"""
Обработчики административной панели
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

from bot.utils.api_client import api_client

router = Router()
logger = logging.getLogger(__name__)


def get_admin_stats_keyboard():
    """Клавиатура для админ-панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin:refresh")],
        [InlineKeyboardButton(text="◀️ В главное меню", callback_data="main_menu")]
    ])


async def format_stats_text(stats: dict) -> str:
    """Форматирование статистики"""
    if not stats:
        return "❌ Не удалось загрузить статистику."

    users = stats.get("users", {})
    measurements = stats.get("measurements", {})
    favorites = stats.get("favorites", {})
    tryons = stats.get("tryons", {})

    text = f"""📊 Статистика бота

👥 Пользователи:
Всего: {users.get('total', 0)}
Новых за сегодня: {users.get('today', 0)}
Новых за 7 дней: {users.get('week', 0)}
Активных за 7 дней: {users.get('active_week', 0)}

📐 Параметры:
Указали параметры: {measurements.get('count', 0)} ({measurements.get('percent', 0):.1f}%)

⭐️ Избранное:
Всего добавлений: {favorites.get('total', 0)}"""

    # Если есть статистика примерок
    if tryons:
        text += f"""

👗 Примерки:
Всего: {tryons.get('total', 0)}
За сегодня: {tryons.get('today', 0)}
За 7 дней: {tryons.get('week', 0)}
Загрузили фото: {tryons.get('users_with_photos', 0)}
Среднее время: {tryons.get('avg_generation_time', 0):.1f} сек
Успешных: {tryons.get('success_rate', 0):.1f}%"""

        # ТОП примерок
        top_tryons = tryons.get('top', [])
        if top_tryons:
            text += "\n\n🔥 ТОП товаров для примерки:"
            for i, item in enumerate(top_tryons[:5], 1):
                text += f"\n{i}. {item.get('name', item.get('product_id'))} - {item.get('count', 0)} примерок"

    return text


@router.message(Command("admin_stats"))
async def show_admin_stats(message: Message):
    """Показать статистику"""
    try:
        # Получаем статистику из API
        result = await api_client.get_admin_stats()

        if result is None:
            await message.answer("❌ Не удалось получить статистику. Сервис недоступен.")
            return

        stats_text = await format_stats_text(result)

        await message.answer(
            stats_text,
            reply_markup=get_admin_stats_keyboard()
        )

    except Exception as e:
        logger.error(f"Failed to get admin stats: {e}")
        await message.answer("❌ Ошибка получения статистики")


@router.callback_query(F.data == "admin:refresh")
async def refresh_admin_stats(callback: CallbackQuery):
    """Обновить статистику"""
    try:
        # Получаем статистику из API
        result = await api_client.get_admin_stats()

        if result is None:
            await callback.answer("❌ Не удалось обновить статистику. Сервис недоступен.", show_alert=True)
            return

        stats_text = await format_stats_text(result)

        # Edit the message only if the text has changed
        if callback.message.text != stats_text:
            await callback.message.edit_text(
                stats_text,
                reply_markup=get_admin_stats_keyboard()
            )
        await callback.answer("✅ Статистика обновлена")

    except Exception as e:
        logger.error(f"Failed to refresh admin stats: {e}")
        await callback.answer("❌ Ошибка обновления", show_alert=True)
