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

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


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

    try:
        # Запуск бота
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot stopped with error: {e}")
