"""
Генерация примерки через Gemini API
"""
import logging
import asyncio
import os
from typing import List, Dict, Any
from datetime import datetime

from gpt_integration.photo_processing.image_client import ImageGenerationClient
from gpt_integration.photo_processing.prompts import (
    TRYON_PROMPT_V1,
    TRYON_PROMPT_V2,
    TRYON_PROMPT_V3,
    TRYON_PROMPT_V4,
    TRYON_PROMPT_V5,
    TRYON_PROMPT_V6,
    TRYON_SINGLE_ITEM,
    TRYON_FULL_OUTFIT,
)

logger = logging.getLogger(__name__)

# Маппинг промптов
PROMPT_VERSIONS = {
    "v1": TRYON_PROMPT_V1,  # Основной (по умолчанию)
    "v2": TRYON_PROMPT_V2,  # Короткий
    "v3": TRYON_PROMPT_V3,  # С примерами
    "v4": TRYON_PROMPT_V4,  # Step-by-step
    "v5": TRYON_PROMPT_V5,  # Технический
    "v6": TRYON_PROMPT_V6,  # Очень короткий
}

# Получаем версию промпта из env (по умолчанию v1)
PROMPT_VERSION = os.getenv("TRYON_PROMPT_VERSION", "v1")
TRYON_PROMPT = PROMPT_VERSIONS.get(PROMPT_VERSION, TRYON_PROMPT_V1)

logger.info(f"Using try-on prompt version: {PROMPT_VERSION}")


# Старый промпт (оставлен для справки)
TRYON_PROMPT_OLD = """Virtual clothing try-on task:

FIRST IMAGE = the person trying on clothes (the customer).
OTHER IMAGES = the clothing items to try on.

IMPORTANT! KEEP FROM THE FIRST IMAGE:
- The person (their face, body type, height, pose, arms, legs, skin tone)
- The background (keep it exactly as is)
- The lighting and color scheme
- The photo quality and style

CHANGE ONLY THE CLOTHING:
- Put the clothing from other images onto THE PERSON FROM THE FIRST IMAGE
- The clothing should fit naturally on their body
- Include realistic fabric folds, draping, and fit
- The clothing should match the person's pose

DO NOT CHANGE:
- The person (DO NOT replace them with the model from the clothing photos!)
- The background (keep the background from the first image!)
- The pose and body position
- The person's physical features

Result: same person, same background, new clothing only."""


async def generate_tryon(
    user_photo_url: str,
    product_photo_urls: List[str],
    api_key: str,
    base_url: str = "https://api.cometapi.com",
    model: str = "gemini-2.5-flash-image",
    timeout: float = 600.0,
    tryon_mode: str = "single_item",
    item_name: str = "одежда"
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
        tryon_mode: Режим примерки:
            - "single_item" - примерить ТОЛЬКО конкретный товар
            - "full_outfit" - примерить ВЕСЬ образ с референса
        item_name: Название товара (используется в режиме single_item)

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

        logger.info(f"🎨 Starting try-on generation with {len(all_image_urls)} images (mode: {tryon_mode})")

        # Выбираем промпт в зависимости от режима
        if tryon_mode == "single_item":
            # Подставляем название товара в промпт
            prompt = TRYON_SINGLE_ITEM.format(item_name=item_name)
            logger.info(f"Using SINGLE_ITEM mode for: {item_name}")
        elif tryon_mode == "full_outfit":
            prompt = TRYON_FULL_OUTFIT
            logger.info("Using FULL_OUTFIT mode")
        else:
            # Fallback на старое поведение (используем выбранную версию промпта)
            prompt = TRYON_PROMPT
            logger.info(f"Using fallback prompt version: {PROMPT_VERSION}")

        # Создаем клиент
        client = ImageGenerationClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            timeout=timeout
        )

        # Генерируем примерку
        result_data_uri = await client.process_images(all_image_urls, prompt)

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
