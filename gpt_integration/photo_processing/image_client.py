import base64
import io
import logging
import time
import asyncio
from typing import Optional, List

import httpx
from PIL import Image
from tenacity import retry, wait_random_exponential, stop_after_attempt

logger = logging.getLogger(__name__)

class ImageGenerationError(Exception):
    """Custom exception for image generation errors."""
    pass

async def download_telegram_photo(file_url: str) -> bytes:
    """
    Download file from Telegram's public file URL.
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(file_url)
        resp.raise_for_status()
        return resp.content

class ImageGenerationClient:
    """
    Клиент для генерации изображений через CometAPI.
    
    Поддерживает модели:
    - Gemini 2.5 Flash Image / Gemini 3 Pro Image
    - GPT Image -1 / GPT Image 1.5 (и другие модели через CometAPI)

    Поддерживает:
    - image→image
    - prompt + одно или несколько изображений
    - возвращает Telegram-ready data:image/png;base64,...
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-pro-image",
        base_url: str = "https://api.cometapi.com",
        timeout: float = 600.0,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout

        # Для прокси-сервисов (CometAPI) формат авторизации может отличаться от стандартного OpenAI
        # Прокси-сервис сам преобразует заголовки при перенаправлении в OpenAI
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"{self.api_key}",
                "Content-Type": "application/json",
                "Accept": "*/*",
            },
            follow_redirects=True,
        )

    async def close(self):
        """Explicit client shutdown."""
        await self.client.aclose()

    @staticmethod
    def _encode_image_to_base64(image_bytes: bytes) -> str:
        """Return raw base64 string (no prefix)."""
        return base64.b64encode(image_bytes).decode("utf-8")

    @staticmethod
    def _decode_base64_image(b64: str) -> bytes:
        """Decode raw base64 → bytes."""
        return base64.b64decode(b64)

    @staticmethod
    def _to_telegram_data_uri(mime: str, b64: str) -> str:
        """Convert raw base64 to Telegram-ready URI."""
        return f"data:{mime};base64,{b64}"

    async def _prepare_image_part(self, image_source: str, for_openai: bool = False):
        """Prepares an image (from URL or local path) for the API.
        
        Args:
            image_source: URL or local path to image
            for_openai: If True, returns OpenAI format (image_url), else Gemini format (inline_data)
        """
        image_bytes = None
        mime_type = "image/png" # Default mime type

        if image_source.startswith(("http://", "https://")):
            logger.debug("Downloading source image from URL: %s", image_source)
            try:
                response = await self.client.get(image_source)
                response.raise_for_status()
                image_bytes = response.content
            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error downloading image {image_source}: {e}")
                raise ImageGenerationError(f"Failed to download image from URL: {image_source}") from e
            except httpx.RequestError as e:
                logger.error(f"Network error downloading image {image_source}: {e}")
                raise ImageGenerationError(f"Network error downloading image from URL: {image_source}") from e
        else:
            logger.debug("Reading source image from local path: %s", image_source)
            try:
                with open(image_source, "rb") as f:
                    image_bytes = f.read()
            except FileNotFoundError as e:
                logger.error(f"Local image file not found: {image_source}")
                raise ImageGenerationError(f"Local image file not found: {image_source}") from e
            except Exception as e:
                logger.error(f"Error reading local image file {image_source}: {e}")
                raise ImageGenerationError(f"Error reading local image file: {image_source}") from e
        
        if not image_bytes:
            raise ImageGenerationError(f"No image data obtained for source: {image_source}")

        try:
            # Try to determine mime type from image content
            img = Image.open(io.BytesIO(image_bytes))
            mime_type = Image.MIME.get(img.format, mime_type)
        except Exception as e:
            logger.warning(f"Could not determine mime type from image content, using default. Error: {e}")

        image_b64 = self._encode_image_to_base64(image_bytes)
        logger.debug("Input mime: %s, size: %d bytes", mime_type, len(image_bytes))
        
        if for_openai:
            # OpenAI format: data URI with mime type
            return {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_b64}"
                }
            }
        else:
            # Gemini format
            return {
                "inline_data": {
                    "mime_type": mime_type,
                    "data": image_b64
                }
            }

    @retry(
        wait=wait_random_exponential(multiplier=1, max=30),
        stop=stop_after_attempt(5),
    )
    async def process_images(
        self,
        image_sources: List[str],
        prompt: str,
    ) -> str:
        """
        image-to-image with multiple inputs:
        - скачивает картинки
        - отправляет запрос в CometAPI/OpenAI API
        - Для Gemini моделей: использует формат Gemini API (generateContent)
        - Для GPT Image моделей: использует формат OpenAI API (chat completions с vision)
        - парсит ответ в зависимости от формата API
        - возвращает data:image/png;base64,...
        """
        start = time.monotonic()

        # Определяем, используем ли мы GPT Image модели
        # ВАЖНО: CometAPI использует формат Gemini API для всех моделей, включая GPT Image
        # Прокси-сервис сам преобразует запросы в формат OpenAI при необходимости
        # Поэтому is_gpt_image используется только для логирования
        model_lower = self.model.lower()
        is_gpt_image = (
            "gpt" in model_lower or 
            "openai" in model_lower
        ) and "gemini" not in model_lower  # Исключаем Gemini модели
        
        logger.info("Model: %s, is_gpt_image: %s (model_lower: %s)", self.model, is_gpt_image, model_lower)
        
        # 1. Download and prepare all images concurrently
        # ВАЖНО: CometAPI использует формат Gemini API для всех моделей, включая GPT Image
        # Поэтому всегда используем формат Gemini (for_openai=False)
        image_parts = await asyncio.gather(
            *[self._prepare_image_part(source, for_openai=False) for source in image_sources]
        )

        # 2. Build request JSON в зависимости от типа модели
        # ВАЖНО: CometAPI использует тот же формат Gemini API для всех моделей, включая GPT Image
        # Прокси-сервис сам преобразует запросы в формат OpenAI при необходимости
        # Поэтому используем формат Gemini API для всех моделей через CometAPI
        parts = [{"text": prompt}]
        parts.extend(image_parts)

        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        endpoint = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
        endpoints_to_try = [endpoint]
        
        if is_gpt_image:
            logger.info("Using Gemini API format for GPT Image model via CometAPI: %s (image-to-image with %d images)", self.model, len(image_sources))
        else:
            logger.info("Using Gemini format for model: %s", self.model)

        resp = None
        last_error = None
        
        for endpoint in endpoints_to_try:
            try:
                logger.info("Trying endpoint: %s, model=%s with %d images", endpoint, self.model, len(image_sources))
                resp = await self.client.post(endpoint, json=body)
                
                if resp.status_code < 400:
                    logger.info("✅ Success with endpoint: %s", endpoint)
                    break
                elif resp.status_code == 404:
                    logger.warning("404 error with endpoint: %s, trying next...", endpoint)
                    continue
                else:
                    # Другие ошибки (400, 500 и т.д.) - логируем и пробуем следующий endpoint
                    error_text = resp.text[:500]  # Ограничиваем длину для логов
                    logger.warning("Error %s with endpoint %s: %s", resp.status_code, endpoint, error_text)
                    continue
            except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning("Connection error with endpoint %s: %s, trying next...", endpoint, type(e).__name__)
                last_error = e
                continue
            except Exception as e:
                logger.warning("Unexpected error with endpoint %s: %s, trying next...", endpoint, e)
                last_error = e
                continue
        
        if resp is None:
            error_msg = f"All endpoints failed for model {self.model}. Tried: {endpoints_to_try}"
            if last_error:
                error_msg += f". Last error: {type(last_error).__name__}: {last_error}"
            logger.error("❌ %s", error_msg)
            raise ImageGenerationError(error_msg) from last_error
        
        if resp.status_code >= 400:
            error_text = resp.text[:1000] if resp.text else "No error message"
            logger.error("API error %s for model %s at endpoint %s: %s", resp.status_code, self.model, endpoint, error_text)
            logger.error("Request body was: %s", str(body)[:500])  # Логируем тело запроса для отладки
            resp.raise_for_status()

        data = resp.json()
        logger.debug("Raw API response received successfully for model %s", self.model)

        # 3. Parse API response
        # ВАЖНО: CometAPI возвращает ответ в формате Gemini API для всех моделей
        try:
            candidates = data.get("candidates") or []
            if not candidates:
                raise ImageGenerationError(f"API returned no candidates for model {self.model}")

            candidate = candidates[0]
            content = candidate.get("content") or {}
            parts = content.get("parts") or []

            output_b64 = None
            output_mime = None

            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")

                if inline:
                    output_mime = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                    output_b64 = inline.get("data")
                    break

            if not output_b64:
                raise ImageGenerationError(
                    f"No image returned by API for model {self.model}. Response: {data}"
                )

        except ImageGenerationError:
            raise
        except Exception as e:
            logger.exception("Failed to parse API response")
            raise ImageGenerationError(f"Failed to parse API response: {e}")

        elapsed = time.monotonic() - start
        logger.info("Image generation execution time for model %s: %.2fs", self.model, elapsed)

        # 4. Prepare final Telegram-ready data:image/...;base64,...
        return self._to_telegram_data_uri(output_mime, output_b64)