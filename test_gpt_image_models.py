"""
Тестовый скрипт для проверки подключения GPT Image моделей через CometAPI.

Важно: GPT Image модели в CometAPI работают через image-edits endpoint:
- POST /v1/images/edits
- multipart/form-data
- Authorization: Bearer {api_key}

Поэтому тест ниже использует реальный клиент `ImageGenerationClient.process_images()`.
"""
import asyncio
import base64
import os
import sys
import tempfile
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent))

from gpt_integration.photo_processing.image_client import ImageGenerationClient, ImageGenerationError
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_model_connection(model_name: str, api_key: str, base_url: str = "https://api.cometapi.com"):
    """
    Тестирует подключение к конкретной модели
    
    Args:
        model_name: Название модели для тестирования
        api_key: API ключ CometAPI
        base_url: Base URL API
    """
    print(f"\n{'='*60}")
    print(f"Тестирование модели: {model_name}")
    print(f"{'='*60}")
    
    client = None
    try:
        # Создаем клиент
        client = ImageGenerationClient(
            api_key=api_key,
            model=model_name,
            base_url=base_url,
            timeout=180.0  # GPT Image может отвечать долго, особенно при генерации
        )
        
        # Минимальный валидный PNG (1x1) для теста
        minimal_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        png_bytes = base64.b64decode(minimal_png_base64)

        # Для /v1/images/generations нужен только prompt
        test_prompt = "A cute baby sea otter, simple style, high quality."

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp.write(png_bytes)
            tmp_path = tmp.name

        try:
            # 1) text→image
            print("\nТестируем через /v1/images/generations (JSON) с ImageGenerationClient.process_images([]) ...")
            result_data_uri = await client.process_images([], test_prompt)

            # 2) image→image (если нужно) — оставляем как дополнительную проверку
            print("\nТестируем через /v1/images/edits (multipart) с ImageGenerationClient.process_images([image]) ...")
            _ = await client.process_images([tmp_path], "Change the image to a minimal colorful test pattern. Keep it tiny.")

            if not (isinstance(result_data_uri, str) and result_data_uri.startswith("data:image/")):
                print("  ❌ Ответ не похож на data:image/*;base64,...")
                print(f"  Получено: {str(result_data_uri)[:200]}")
                return False

            print("  ✅ УСПЕХ! Получили изображение в формате data URI.")
            return True
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            
    except Exception as e:
        print(f"\n❌ Критическая ошибка при тестировании модели '{model_name}': {e}")
        logger.exception("Full error traceback:")
        return False
    finally:
        if client:
            await client.close()


async def main():
    """Основная функция тестирования"""
    print("="*60)
    print("ТЕСТ ПОДКЛЮЧЕНИЯ К GPT IMAGE МОДЕЛЯМ")
    print("="*60)
    
    # Получаем API ключ из переменных окружения
    api_key = os.getenv("COMET_API_KEY") or os.getenv("IMAGE_GEN_API_KEY")
    if not api_key:
        print("\nОШИБКА: Не найден API ключ!")
        print("Установите переменную окружения COMET_API_KEY или IMAGE_GEN_API_KEY")
        print("\nПример:")
        print("  export COMET_API_KEY='your-api-key'")
        print("  или")
        print("  set COMET_API_KEY=your-api-key  (Windows)")
        return
    
    base_url = os.getenv("COMET_BASE_URL", "https://api.cometapi.com")
    print(f"\nAPI Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else '***'}")
    print(f"Base URL: {base_url}")
    
    # Список моделей для тестирования (только GPT Image модели)
    models_to_test = [
        "gpt-image-1.5",
    ]
    
    print(f"\nБудет протестировано {len(models_to_test)} моделей")
    print("="*60)
    
    results = {}
    
    for model in models_to_test:
        result = await test_model_connection(model, api_key, base_url)
        results[model] = result
        await asyncio.sleep(1)  # Небольшая пауза между запросами
    
    # Итоговый отчет
    print("\n" + "="*60)
    print("ИТОГОВЫЙ ОТЧЕТ")
    print("="*60)
    
    working_models = [m for m, r in results.items() if r]
    failed_models = [m for m, r in results.items() if not r]
    
    print(f"\nРабочие модели ({len(working_models)}):")
    for model in working_models:
        print(f"   - {model}")
    
    print(f"\nНе работающие модели ({len(failed_models)}):")
    for model in failed_models:
        print(f"   - {model}")
    
    print("\n" + "="*60)
    print("РЕКОМЕНДАЦИИ:")
    print("="*60)
    
    if working_models:
        print("\nИспользуйте рабочие модели в маппинге:")
        for model in working_models:
            if "gpt" in model.lower() or "openai" in model.lower():
                print(f"   - {model}")
    else:
        print("\nGPT Image модели не работают. Возможные причины:")
        print("   1. Модели недоступны в вашем тарифе CometAPI")
        print("   2. Неверные названия моделей (проверьте документацию)")
        print("   3. Требуется другой формат запроса для этих моделей")
        print("   4. Модели используют другой endpoint (не Gemini-совместимый)")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())
