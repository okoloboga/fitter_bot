"""
Главный файл для запуска бота
"""
import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from bot.handlers import register_handlers
from bot.services.photo_preloader import photo_preloader
from bot.utils.api_client import api_client

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def wait_for_api_ready(max_retries: int = 10, delay: int = 3):
    """
    Ожидание готовности API сервера

    Args:
        max_retries: Максимальное количество попыток
        delay: Задержка между попытками в секундах
    """
    logger.info("Waiting for API to be ready...")

    for attempt in range(1, max_retries + 1):
        try:
            categories = await api_client.get_categories()
            if categories is not None:
                logger.info("✅ API is ready!")
                return True
        except Exception as e:
            logger.warning(f"Attempt {attempt}/{max_retries}: API not ready yet ({e})")

        if attempt < max_retries:
            await asyncio.sleep(delay)

    logger.error("❌ API is not available after maximum retries")
    return False


async def preload_product_photos():
    """Предзагрузка и оптимизация фото всех товаров"""
    logger.info("=" * 60)
    logger.info("Starting product photos preload...")
    logger.info("=" * 60)

    try:
        # Ожидаем готовности API
        if not await wait_for_api_ready():
            logger.error("Cannot preload photos: API is not available")
            return

        # Получаем все категории
        categories = await api_client.get_categories()
        if not categories:
            logger.warning("No categories found. Skipping photo preload.")
            return

        # Собираем все товары из всех категорий
        all_products = []
        for category in categories:
            products = await api_client.get_products_by_category(category['category_id'])
            all_products.extend(products)

        if not all_products:
            logger.warning("No products found. Skipping photo preload.")
            return

        logger.info(f"Found {len(all_products)} products across {len(categories)} categories")

        # Запускаем предзагрузку
        stats = await photo_preloader.preload_product_photos(all_products)

        # Очистка устаревших фото
        active_product_ids = [p['product_id'] for p in all_products]
        photo_preloader.cleanup_orphaned_photos(active_product_ids)

        # Статистика хранилища
        storage_stats = photo_preloader.get_stats()

        logger.info("=" * 60)
        logger.info("Photo preload completed!")
        logger.info(f"  Total photos: {stats['total']}")
        logger.info(f"  Downloaded: {stats['downloaded']}")
        logger.info(f"  Skipped (already exists): {stats['skipped']}")
        logger.info(f"  Failed: {stats['failed']}")
        logger.info(f"  Storage: {storage_stats['total_files']} files, {storage_stats['total_size_mb']} MB")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during photo preload: {e}", exc_info=True)


async def background_photo_updater(interval_minutes: int = 30):
    """
    Фоновая задача для периодического обновления фото товаров

    Args:
        interval_minutes: Интервал проверки в минутах (по умолчанию 30)
    """
    logger.info(f"Background photo updater started (interval: {interval_minutes} min)")

    while True:
        try:
            # Ждем указанное время
            await asyncio.sleep(interval_minutes * 60)

            logger.info("Running scheduled photo update...")
            await preload_product_photos()

        except asyncio.CancelledError:
            logger.info("Background photo updater stopped")
            break
        except Exception as e:
            logger.error(f"Error in background photo updater: {e}", exc_info=True)


async def main():
    """Главная функция запуска бота"""

    # Получаем токен бота
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables!")
        return

    # Настройка Redis для FSM storage
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_db = int(os.getenv("REDIS_DB", 0))

    try:
        # Подключение к Redis
        redis = Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=True
        )

        # Проверка подключения к Redis
        await redis.ping()
        logger.info(f"Connected to Redis at {redis_host}:{redis_port}")

        storage = RedisStorage(redis=redis)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        logger.info("Using MemoryStorage as fallback")
        from aiogram.fsm.storage.memory import MemoryStorage
        storage = MemoryStorage()

    # Инициализация бота и диспетчера
    bot = Bot(token=bot_token)
    dp = Dispatcher(storage=storage)

    # Регистрация обработчиков
    router = register_handlers()
    dp.include_router(router)

    logger.info("Bot is starting...")

    # Предзагрузка фото товаров при старте
    await preload_product_photos()

    # Запускаем фоновую задачу обновления фото
    update_interval_minutes = int(os.getenv("PHOTO_UPDATE_INTERVAL_MINUTES", "30"))
    background_task = asyncio.create_task(background_photo_updater(update_interval_minutes))

    try:
        # Запуск бота
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        # Останавливаем фоновую задачу
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass

        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
