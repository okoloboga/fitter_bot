"""
Утилиты для обработки изображений
"""
import io
import logging
from typing import Optional

import aiohttp
from PIL import Image
from cachetools import TTLCache
from aiogram.types import BufferedInputFile

logger = logging.getLogger(__name__)

# Кеш для обработанных изображений (храним 100 фото в течение 1 часа)
image_cache = TTLCache(maxsize=100, ttl=3600)

MAX_SIZE = (1280, 1280)
JPEG_QUALITY = 85


async def get_optimized_photo(url: str) -> Optional[BufferedInputFile]:
    """
    Скачивает, оптимизирует (сжимает и изменяет размер) и кеширует изображение.

    Args:
        url: URL исходного изображения.

    Returns:
        BufferedInputFile с оптимизированным изображением или None в случае ошибки.
    """
    if not url or not isinstance(url, str) or not url.strip():
        return None

    # Проверяем кеш
    if url in image_cache:
        logger.info(f"Image found in cache: {url}")
        return BufferedInputFile(image_cache[url], filename="photo.jpg")

    logger.info(f"Optimizing image from URL: {url}")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Failed to download image {url}. Status: {response.status}")
                    return None
                image_data = await response.read()

        with Image.open(io.BytesIO(image_data)) as img:
            # Конвертируем в RGB, если есть альфа-канал (для сохранения в JPEG)
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')

            # Уменьшаем размер, сохраняя пропорции
            img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)

            # Сохраняем в буфер с сжатием
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=JPEG_QUALITY)
            buffer.seek(0)
            optimized_data = buffer.read()

            # Сохраняем в кеш
            image_cache[url] = optimized_data
            logger.info(f"Image optimized and cached successfully. Original size: {len(image_data)}, Optimized size: {len(optimized_data)}")

            return BufferedInputFile(optimized_data, filename="photo.jpg")

    except Exception as e:
        logger.error(f"Error processing image from URL {url}: {e}", exc_info=True)
        return None
