# Сравнение OpenAI API и текущей реализации через CometAPI

## Ключевое различие

**OpenAI API** (`platform.openai.com`) и **CometAPI** (`api.cometapi.com`) - это разные сервисы:
- OpenAI API - прямой доступ к моделям OpenAI
- CometAPI - прокси-сервис, который предоставляет единый интерфейс для разных AI моделей

---

## 1. OPENAI API ДЛЯ IMAGE EDITS

### Endpoint
```
POST https://api.openai.com/v1/images/edits
```

### Формат запроса
**Content-Type:** `multipart/form-data`

**Параметры:**
- `image` (file, required) - PNG изображение, <4MB, квадратное
- `mask` (file, optional) - PNG маска, указывает области для редактирования
- `prompt` (string, required) - Описание полного нового изображения
- `model` (string, optional) - `"dall-e-2"` (только DALL·E 2 поддерживает редактирование)
- `n` (integer, optional) - Количество вариантов (1-10)
- `size` (string, optional) - `"1024x1024"`, `"512x512"`, `"256x256"`

### Формат ответа
```json
{
  "created": 1589478378,
  "data": [
    {
      "url": "https://...",
      "b64_json": "..." // опционально, если response_format=b64_json
    }
  ]
}
```

### Авторизация
```
Authorization: Bearer {api_key}
```

---

## 2. ТЕКУЩАЯ РЕАЛИЗАЦИЯ (CometAPI)

### Endpoint
```
POST https://api.cometapi.com/v1beta/models/{model}:generateContent
```

### Формат запроса
**Content-Type:** `application/json`

**Структура:**
```json
{
  "contents": [
    {
      "role": "user",
      "parts": [
        {"text": "prompt"},
        {
          "inline_data": {
            "mime_type": "image/png",
            "data": "base64_encoded_image"
          }
        }
      ]
    }
  ],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"]
  }
}
```

### Формат ответа
```json
{
  "candidates": [
    {
      "content": {
        "parts": [
          {
            "inlineData": {
              "mimeType": "image/png",
              "data": "base64_encoded_image"
            }
          }
        ]
      }
    }
  ]
}
```

### Авторизация
```
Authorization: {api_key}  // БЕЗ "Bearer"
```

---

## 3. КРИТИЧЕСКИЕ РАЗЛИЧИЯ

| Параметр | OpenAI API | CometAPI (текущая реализация) | Статус |
|----------|------------|-------------------------------|--------|
| **Endpoint** | `/v1/images/edits` | `/v1beta/models/{model}:generateContent` | ❌ Разные |
| **Content-Type** | `multipart/form-data` | `application/json` | ❌ Разные |
| **Формат изображений** | Файлы (multipart) | Base64 в JSON | ❌ Разные |
| **Структура запроса** | Плоские параметры | Вложенная структура `contents` | ❌ Разные |
| **Формат ответа** | `data[0].url` или `data[0].b64_json` | `candidates[0].content.parts[].inlineData.data` | ❌ Разные |
| **Авторизация** | `Bearer {api_key}` | `{api_key}` | ❌ Разные |
| **Модели** | `dall-e-2`, `dall-e-3` | `gpt-image-1.5` | ❌ Разные |

---

## 4. ВАЖНЫЙ ВЫВОД

**Текущая реализация НЕ использует OpenAI API напрямую!**

CometAPI является прокси-сервисом, который:
1. Принимает запросы в формате Gemini API
2. Преобразует их для нужной модели (Gemini, GPT Image, и т.д.)
3. Возвращает ответ в формате Gemini API

Это означает:
- ✅ Текущий формат запроса (Gemini API) **правильный** для CometAPI
- ✅ Endpoint `/v1beta/models/{model}:generateContent` **правильный** для CometAPI
- ⚠️ НО нужно проверить в документации CometAPI:
  - Правильные названия моделей GPT Image
  - Нужны ли дополнительные параметры
  - Правильный ли формат авторизации

---

## 5. ЧТО НУЖНО ПРОВЕРИТЬ В ДОКУМЕНТАЦИИ COMETAPI

### 5.1 Документация: https://apidoc.cometapi.com/image-edits

**Проверить:**
1. ✅ Используется ли тот же endpoint `/v1beta/models/{model}:generateContent`?
2. ✅ Используется ли тот же формат запроса (Gemini API)?
3. ✅ Какие точные названия моделей GPT Image?
4. ✅ Нужны ли дополнительные параметры в `generationConfig`?
5. ✅ Правильный ли формат авторизации?

### 5.2 Документация: https://platform.openai.com/docs/api-reference/images/createEdit

**Эта документация НЕ относится к CometAPI!**

Эта документация описывает:
- Прямой доступ к OpenAI API
- Формат `multipart/form-data`
- Endpoint `/v1/images/edits`
- Модели `dall-e-2`, `dall-e-3`

**НО:** CometAPI может использовать другой формат, даже для GPT Image моделей!

---

## 6. РЕКОМЕНДАЦИИ

### Если CometAPI использует Gemini API формат для всех моделей:
✅ **Текущая реализация правильная** - никаких изменений не требуется

### Если CometAPI требует другой формат для GPT Image:
❌ **Нужно добавить поддержку** другого формата:
- Определить тип модели (GPT Image vs Gemini)
- Использовать соответствующий формат запроса
- Парсить ответ в соответствующем формате

### Что проверить в первую очередь:
1. **Документация CometAPI** (`https://apidoc.cometapi.com/image-edits`)
   - Это главный источник информации
   - Проверить формат для GPT Image моделей

2. **Тестирование**
   - Запустить `test_gpt_image_models.py`
   - Проверить, работает ли текущий формат для GPT Image моделей

---

## 7. ВОЗМОЖНЫЕ СЦЕНАРИИ

### Сценарий 1: CometAPI использует Gemini API для всех моделей
**Текущая реализация:** ✅ Правильная
**Действия:** Никаких изменений не требуется

### Сценарий 2: CometAPI требует OpenAI API формат для GPT Image
**Текущая реализация:** ❌ Неправильная
**Действия:**
- Добавить определение типа модели
- Добавить поддержку `multipart/form-data` для GPT Image
- Добавить парсинг ответа в формате OpenAI API

### Сценарий 3: CometAPI использует свой собственный формат
**Текущая реализация:** ❌ Неправильная
**Действия:**
- Изучить документацию CometAPI
- Реализовать специфичный формат для GPT Image

---

## 8. ПЛАН ДЕЙСТВИЙ

1. **Проверить документацию CometAPI** (`https://apidoc.cometapi.com/image-edits`)
   - Найти формат для GPT Image моделей
   - Сравнить с текущей реализацией

2. **Протестировать текущую реализацию**
   - Запустить тесты с моделью `gpt-image-1.5`
   - Проверить, работают ли они с текущим форматом

3. **Внести изменения (если требуется)**
   - Добавить поддержку другого формата
   - Обновить парсинг ответов

---

## 9. ВЫВОД

**OpenAI API документация** (`platform.openai.com/docs/api-reference/images/createEdit`) описывает прямой доступ к OpenAI API, который **НЕ используется** в текущей реализации.

**CometAPI** использует свой формат (вероятно, Gemini API формат для всех моделей), поэтому нужно проверять документацию CometAPI, а не OpenAI API.

**Главный вопрос:** Использует ли CometAPI тот же Gemini API формат для GPT Image моделей, или нужен другой формат?

**Ответ:** Нужно проверить в документации CometAPI (`https://apidoc.cometapi.com/image-edits`)
