"""
Тестовый скрипт для проверки подключения GPT Image моделей через CometAPI
"""
import asyncio
import os
import sys
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
            timeout=30.0  # Короткий таймаут для теста
        )
        
        # Создаем простой тестовый промпт и изображение
        # Используем минимальный тестовый запрос
        test_prompt = "Generate a simple test image"
        
        # Для теста используем простой base64 изображение (1x1 пиксель PNG)
        # Это минимальный валидный PNG в base64
        minimal_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        
        # Формируем тестовый body
        test_body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": test_prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": minimal_png_base64
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"]
            }
        }
        
        # Пробуем разные endpoint'ы
        endpoints_to_try = []
        if "gpt" in model_name.lower() or "openai" in model_name.lower():
            endpoints_to_try = [
                f"{base_url}/v1beta/models/{model_name}:generateContent",
                f"{base_url}/v1/images/generations",
                f"{base_url}/v1/chat/completions",
            ]
        else:
            endpoints_to_try = [f"{base_url}/v1beta/models/{model_name}:generateContent"]
        
        print(f"\nПробуем {len(endpoints_to_try)} endpoint(ов)...")
        
        success = False
        for i, endpoint in enumerate(endpoints_to_try, 1):
            print(f"\n[{i}/{len(endpoints_to_try)}] Тестируем endpoint: {endpoint}")
            try:
                resp = await client.client.post(endpoint, json=test_body)
                
                print(f"  Статус: {resp.status_code}")
                
                if resp.status_code < 400:
                    print(f"  ✅ УСПЕХ! Endpoint работает!")
                    try:
                        data = resp.json()
                        print(f"  Ответ содержит ключи: {list(data.keys())}")
                        success = True
                        break
                    except Exception as e:
                        print(f"  ⚠️ Не удалось распарсить JSON: {e}")
                        print(f"  Текст ответа (первые 200 символов): {resp.text[:200]}")
                        success = True  # Но endpoint ответил
                        break
                elif resp.status_code == 404:
                    print(f"  ❌ 404 - Endpoint не найден")
                    if resp.text:
                        print(f"  Сообщение: {resp.text[:200]}")
                elif resp.status_code == 401:
                    print(f"  ❌ 401 - Проблема с авторизацией (проверьте API ключ)")
                    if resp.text:
                        print(f"  Сообщение: {resp.text[:200]}")
                elif resp.status_code == 400:
                    print(f"  ❌ 400 - Неверный формат запроса")
                    if resp.text:
                        print(f"  Сообщение: {resp.text[:200]}")
                else:
                    print(f"  ❌ Ошибка {resp.status_code}")
                    if resp.text:
                        print(f"  Сообщение: {resp.text[:500]}")
                        
            except Exception as e:
                error_type = type(e).__name__
                print(f"  ❌ Исключение: {error_type}: {str(e)[:200]}")
                if "RemoteProtocolError" in error_type:
                    print(f"     → Сервер разорвал соединение без ответа")
                elif "ConnectError" in error_type:
                    print(f"     → Ошибка подключения")
                elif "TimeoutException" in error_type:
                    print(f"     → Таймаут соединения")
        
        if success:
            print(f"\n✅ Модель '{model_name}' РАБОТАЕТ!")
            return True
        else:
            print(f"\n❌ Модель '{model_name}' НЕ РАБОТАЕТ со всеми endpoint'ами")
            return False
            
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
        print("\n❌ ОШИБКА: Не найден API ключ!")
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
        "gpt-image-1",
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
    
    print(f"\n✅ Рабочие модели ({len(working_models)}):")
    for model in working_models:
        print(f"   - {model}")
    
    print(f"\n❌ Не работающие модели ({len(failed_models)}):")
    for model in failed_models:
        print(f"   - {model}")
    
    print("\n" + "="*60)
    print("РЕКОМЕНДАЦИИ:")
    print("="*60)
    
    if working_models:
        print("\n✅ Используйте рабочие модели в маппинге:")
        for model in working_models:
            if "gpt" in model.lower() or "openai" in model.lower():
                print(f"   - {model}")
    else:
        print("\n⚠️ GPT Image модели не работают. Возможные причины:")
        print("   1. Модели недоступны в вашем тарифе CometAPI")
        print("   2. Неверные названия моделей (проверьте документацию)")
        print("   3. Требуется другой формат запроса для этих моделей")
        print("   4. Модели используют другой endpoint (не Gemini-совместимый)")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(main())
