"""
Генерация примерки через Gemini API
"""
import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime

from gpt_integration.photo_processing.image_client import ImageGenerationClient

logger = logging.getLogger(__name__)


TRYON_PROMPT = """Создай реалистичное изображение, где человек с первого фото одет в одежду с других фото.
Сохрани черты лица, прическу и позу человека.
Одежда должна выглядеть естественно на фигуре с учетом складок и драпировки.
Сохрани фон из оригинального фото пользователя."""


async def generate_tryon(
    user_photo_url: str,
    product_photo_urls: List[str],
    api_key: str,
    base_url: str = "https://api.cometapi.com",
    model: str = "gemini-2.5-flash-image",
    timeout: float = 180.0
) -> Dict[str, Any]:
    """
    Генерация примерки через Gemini API (CometAPI)

    Args:
        user_photo_url: URL фото пользователя
        product_photo_urls: Список URL фото товара (до 2 штук)
        api_key: API ключ для CometAPI
        base_url: Base URL API (по умолчанию https://api.cometapi.com)
        model: Модель для генерации:
            - "gemini-2.5-flash-image" - Nano Banana (быстро)
            - "gemini-3-pro-image" - Nano Banana Pro (дольше, качественнее)
        timeout: Таймаут в секундах

    Returns:
        Dict с ключами: success, result/error
    """
    start_time = datetime.now()
    client = None

    try:
        # Ограничиваем до 2 фото товара (всего 3 с фото пользователя)
        product_urls = product_photo_urls[:2]

        # Собираем все URL: фото пользователя + фото товара
        all_image_urls = [user_photo_url] + product_urls

        logger.info(f"🎨 Starting try-on generation with {len(all_image_urls)} images")

        # Создаем клиент
        client = ImageGenerationClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout
        )

        # Генерируем примерку
        result_data_uri = await client.process_images(all_image_urls, TRYON_PROMPT)

        processing_time = (datetime.now() - start_time).total_seconds()

        logger.info(f"✅ Try-on generated successfully in {processing_time:.2f}s")

        return {
            "success": True,
            "result": {
                "photo_url": result_data_uri,
                "processing_time": int(processing_time)
            }
        }

    except asyncio.TimeoutError:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Try-on generation timeout after {processing_time:.2f}s")
        return {
            "success": False,
            "error": {
                "type": "timeout",
                "message": "Превышено время ожидания генерации"
            }
        }

    except Exception as e:
        processing_time = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ Try-on generation failed after {processing_time:.2f}s: {e}", exc_info=True)

        error_str = str(e).lower()
        if "timeout" in error_str:
            error_type = "timeout"
            message = "Превышено время ожидания генерации"
        elif "api" in error_str or "network" in error_str:
            error_type = "api_error"
            message = "Ошибка при обращении к сервису генерации"
        else:
            error_type = "processing_error"
            message = f"Ошибка генерации: {str(e)}"

        return {
            "success": False,
            "error": {
                "type": error_type,
                "message": message
            }
        }

    finally:
        if client:
            await client.close()
