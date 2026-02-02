# Исправления для GPT Image моделей - Применено

## Источник документации
**CometAPI Image Edits:** https://apidoc.cometapi.com/image-edits

---

## Критические различия обнаружены

Согласно документации CometAPI, GPT Image модели используют **совершенно другой формат**, чем Gemini модели:

| Параметр | Gemini модели | GPT Image модели |
|----------|---------------|------------------|
| **Endpoint** | `/v1beta/models/{model}:generateContent` | `/v1/images/edits` |
| **Формат запроса** | `application/json` | `multipart/form-data` |
| **Авторизация** | `{api_key}` | `Bearer {api_key}` |
| **Параметры** | `contents`, `generationConfig` | `image`, `prompt`, `model`, `quality`, `size` |
| **Формат ответа** | `candidates[0].content.parts[].inlineData.data` | `data[0].b64_json` |

---

## Внесенные изменения

### 1. ✅ Обновлен endpoint для GPT Image моделей

**Файл:** `gpt_integration/photo_processing/image_client.py`

**Было:**
```python
endpoint = f"{self.base_url}/v1beta/models/{self.model}:generateContent"
```

**Стало:**
- Для Gemini: `/v1beta/models/{model}:generateContent`
- Для GPT Image: `/v1/images/edits`

---

### 2. ✅ Изменен формат запроса для GPT Image моделей

**Файл:** `gpt_integration/photo_processing/image_client.py`

**Было:**
```python
# JSON формат для всех моделей
body = {
    "contents": [{"role": "user", "parts": [...]}],
    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
}
resp = await self.client.post(endpoint, json=body)
```

**Стало:**
- Для Gemini: JSON формат (без изменений)
- Для GPT Image: `multipart/form-data`:
```python
files = {
    "image": (filename, image_bytes, mime_type)
}
data = {
    "prompt": prompt,
    "model": self.model,
    "response_format": "b64_json",
    "quality": "high",
    "size": "auto",
}
resp = await client.post(endpoint, files=files, data=data, headers=headers)
```

---

### 3. ✅ Обновлена авторизация для GPT Image моделей

**Файл:** `gpt_integration/photo_processing/image_client.py`

**Было:**
```python
headers = {"Authorization": f"{self.api_key}"}
```

**Стало:**
- Для Gemini: `Authorization: {api_key}` (без изменений)
- Для GPT Image: `Authorization: Bearer {api_key}`

---

### 4. ✅ Обновлен парсинг ответа для GPT Image моделей

**Файл:** `gpt_integration/photo_processing/image_client.py`

**Было:**
```python
# Парсинг Gemini API формата
candidates = data.get("candidates") or []
candidate = candidates[0]
content = candidate.get("content") or {}
parts = content.get("parts") or []
inline = part.get("inlineData")
output_b64 = inline.get("data")
```

**Стало:**
- Для Gemini: Парсинг Gemini API формата (без изменений)
- Для GPT Image: Парсинг OpenAI API формата:
```python
response_data = resp.json()
output_b64 = response_data["data"][0].get("b64_json")
```

---

### 5. ✅ Добавлена поддержка параметров для GPT Image моделей

**Файл:** `gpt_integration/photo_processing/image_client.py`

**Добавлены параметры:**
- `quality`: `"high"` (для gpt-image-1: "high", "medium", "low", "auto")
- `size`: `"auto"` (для gpt-image-1: "1024x1024", "1536x1024", "1024x1536", "auto")
- `response_format`: `"b64_json"` (для получения base64 напрямую)

---

### 6. ✅ Обновлены названия моделей

**Файл:** `bot/handlers/tryon.py`

**Примечание:**
В рамках этой задачи мы **явно используем модель `gpt-image-1.5`**, как указано в документации/ссылке CometAPI image-edits и требованиях интеграции.

**Изменения:**
```python
# Было:
"gpt-image-1.5": ("gpt-image-1.5", "GPT Image 1.5")

# Стало:
"gpt-image-1.5": ("gpt-image-1.5", "GPT Image 1.5")
```

---

## Структура кода после изменений

### Метод `process_images()`
Теперь определяет тип модели и вызывает соответствующий метод:

```python
async def process_images(self, image_sources: List[str], prompt: str) -> str:
    is_gpt_image = ("gpt-image" in model_lower or ...) and "gemini" not in model_lower
    
    if is_gpt_image:
        return await self._process_images_gpt_image(image_sources, prompt, start)
    else:
        return await self._process_images_gemini(image_sources, prompt, start)
```

### Метод `_process_images_gpt_image()`
Новый метод для обработки GPT Image моделей:
- Использует endpoint `/v1/images/edits`
- Отправляет `multipart/form-data`
- Использует авторизацию `Bearer {api_key}`
- Парсит ответ в формате OpenAI API

### Метод `_process_images_gemini()`
Выделен отдельный метод для Gemini моделей:
- Использует endpoint `/v1beta/models/{model}:generateContent`
- Отправляет JSON
- Использует авторизацию `{api_key}`
- Парсит ответ в формате Gemini API

---

## Ограничения GPT Image моделей

Согласно документации CometAPI:

1. **Только одно изображение:**
   - GPT Image модели принимают только одно изображение в параметре `image`
   - Если передано несколько изображений, используется первое (основное фото пользователя)

2. **Размер изображения:**
   - Для `gpt-image-1`: PNG или JPG, каждый <25MB
   - Для `dall-e-3`: 1 квадратное PNG <4MB

3. **Длина промпта:**
   - Для `dall-e-3`: максимум 1000 символов
   - Для `gpt-image-1`: максимум 32000 символов

---

## Тестирование

После внесения изменений необходимо протестировать:

1. ✅ Модель `gpt-image-1.5` (используется напрямую)
3. ✅ Gemini модели - должны продолжать работать как раньше
4. ✅ Обработка ошибок для обоих типов моделей

---

## Следующие шаги

1. **Протестировать изменения:**
   - Запустить тесты с моделью `gpt-image-1.5`
   - Проверить, что Gemini модели продолжают работать

2. **Опционально - добавить поддержку других параметров:**
   - Параметр `mask` для редактирования конкретных областей
   - Параметр `n` для генерации нескольких вариантов
   - Настройка `quality` и `size` через параметры функции

3. **Обновить документацию:**
   - Обновить комментарии в коде
   - Обновить документацию проекта

---

## Выводы

✅ **Все критические исправления применены:**
- Endpoint обновлен
- Формат запроса изменен на multipart/form-data для GPT Image
- Авторизация обновлена на Bearer для GPT Image
- Парсинг ответа обновлен на OpenAI API формат
- Добавлены параметры quality, size, response_format
- Название модели `gpt-image-1.5` используется напрямую (без подмены на `mini`)

✅ **Код теперь соответствует документации CometAPI**

⚠️ **Требуется тестирование** для подтверждения работоспособности
