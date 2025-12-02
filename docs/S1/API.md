# API Documentation - Fitting Bot

Полная документация REST API для Telegram бота по подбору одежды.

**Base URL:** `http://localhost:8000`

**Swagger UI:** http://localhost:8000/docs

---

## Общая информация

### Формат ответов

Все ответы возвращаются в JSON формате.

### Коды ответов

- `200` - Успешный запрос
- `404` - Ресурс не найден
- `422` - Ошибка валидации
- `500` - Внутренняя ошибка сервера

---

## 1. Users API

Управление пользователями бота.

### 1.1 Регистрация пользователя

**Endpoint:** `POST /api/users/register`

**Описание:** Создает нового пользователя или возвращает существующего по `tg_id`.

**Request Body:**
```json
{
  "tg_id": 123456789,
  "username": "john_doe",
  "first_name": "John"
}
```

**Параметры:**
- `tg_id` (integer, обязательно) - Telegram ID пользователя
- `username` (string, опционально) - Username в Telegram
- `first_name` (string, опционально) - Имя пользователя

**Response:** `200 OK`
```json
{
  "id": 1,
  "tg_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "created_at": "2024-12-02T10:00:00Z",
  "last_activity": "2024-12-02T10:00:00Z",
  "is_admin": false
}
```

**Пример curl:**
```bash
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "tg_id": 123456789,
    "username": "john_doe",
    "first_name": "John"
  }'
```

---

### 1.2 Получить пользователя по ID

**Endpoint:** `GET /api/users/{user_id}`

**Описание:** Возвращает информацию о пользователе по внутреннему ID.

**Path Parameters:**
- `user_id` (integer) - ID пользователя в БД

**Response:** `200 OK`
```json
{
  "id": 1,
  "tg_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "created_at": "2024-12-02T10:00:00Z",
  "last_activity": "2024-12-02T10:00:00Z",
  "is_admin": false
}
```

**Response:** `404 Not Found`
```json
{
  "detail": "User not found"
}
```

**Пример curl:**
```bash
curl "http://localhost:8000/api/users/1"
```

---

### 1.3 Получить пользователя по Telegram ID

**Endpoint:** `GET /api/users/by-tg-id/{tg_id}`

**Описание:** Возвращает информацию о пользователе по Telegram ID.

**Path Parameters:**
- `tg_id` (integer) - Telegram ID пользователя

**Response:** `200 OK`
```json
{
  "id": 1,
  "tg_id": 123456789,
  "username": "john_doe",
  "first_name": "John",
  "created_at": "2024-12-02T10:00:00Z",
  "last_activity": "2024-12-02T10:00:00Z",
  "is_admin": false
}
```

**Пример curl:**
```bash
curl "http://localhost:8000/api/users/by-tg-id/123456789"
```

---

### 1.4 Обновить активность пользователя

**Endpoint:** `PUT /api/users/{user_id}/activity`

**Описание:** Обновляет время последней активности пользователя.

**Path Parameters:**
- `user_id` (integer) - ID пользователя в БД

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "Activity updated"
}
```

**Пример curl:**
```bash
curl -X PUT "http://localhost:8000/api/users/1/activity"
```

---

## 2. Measurements API

Управление параметрами тела пользователей.

### 2.1 Создать/обновить параметры

**Endpoint:** `POST /api/measurements/{user_id}`

**Описание:** Создает новые или обновляет существующие параметры пользователя.

**Path Parameters:**
- `user_id` (integer) - ID пользователя в БД

**Request Body:**
```json
{
  "height": 165,
  "chest": 85,
  "waist": 65,
  "hips": 95
}
```

**Параметры:**
- `height` (integer, 140-200) - Рост в сантиметрах
- `chest` (integer, 70-130) - Обхват груди в см
- `waist` (integer, 50-110) - Обхват талии в см
- `hips` (integer, 70-140) - Обхват бедер в см

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "height": 165,
  "chest": 85,
  "waist": 65,
  "hips": 95,
  "updated_at": "2024-12-02T10:05:00Z"
}
```

**Response:** `404 Not Found`
```json
{
  "detail": "User not found"
}
```

**Response:** `422 Validation Error`
```json
{
  "detail": [
    {
      "loc": ["body", "height"],
      "msg": "ensure this value is greater than or equal to 140",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

**Пример curl:**
```bash
curl -X POST "http://localhost:8000/api/measurements/1" \
  -H "Content-Type: application/json" \
  -d '{
    "height": 165,
    "chest": 85,
    "waist": 65,
    "hips": 95
  }'
```

---

### 2.2 Получить параметры пользователя

**Endpoint:** `GET /api/measurements/{user_id}`

**Описание:** Возвращает параметры тела пользователя.

**Path Parameters:**
- `user_id` (integer) - ID пользователя в БД

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "height": 165,
  "chest": 85,
  "waist": 65,
  "hips": 95,
  "updated_at": "2024-12-02T10:05:00Z"
}
```

**Response:** `404 Not Found`
```json
{
  "detail": "Measurements not found"
}
```

**Пример curl:**
```bash
curl "http://localhost:8000/api/measurements/1"
```

---

## 3. Favorites API

Управление избранными товарами.

### 3.1 Добавить в избранное

**Endpoint:** `POST /api/favorites/`

**Описание:** Добавляет товар в избранное пользователя.

**Request Body:**
```json
{
  "user_id": 1,
  "product_id": "jacket_001"
}
```

**Параметры:**
- `user_id` (integer) - ID пользователя в БД
- `product_id` (string) - ID товара из Google Sheets

**Response:** `200 OK`
```json
{
  "id": 1,
  "user_id": 1,
  "product_id": "jacket_001",
  "added_at": "2024-12-02T10:10:00Z"
}
```

**Примечание:** Если товар уже в избранном, возвращается существующая запись.

**Пример curl:**
```bash
curl -X POST "http://localhost:8000/api/favorites/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "product_id": "jacket_001"
  }'
```

---

### 3.2 Удалить из избранного

**Endpoint:** `DELETE /api/favorites/{user_id}/{product_id}`

**Описание:** Удаляет товар из избранного пользователя.

**Path Parameters:**
- `user_id` (integer) - ID пользователя в БД
- `product_id` (string) - ID товара из Google Sheets

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "Removed from favorites"
}
```

**Пример curl:**
```bash
curl -X DELETE "http://localhost:8000/api/favorites/1/jacket_001"
```

---

### 3.3 Получить список избранного

**Endpoint:** `GET /api/favorites/{user_id}`

**Описание:** Возвращает все избранные товары пользователя, отсортированные по дате добавления (новые первыми).

**Path Parameters:**
- `user_id` (integer) - ID пользователя в БД

**Response:** `200 OK`
```json
[
  {
    "id": 2,
    "user_id": 1,
    "product_id": "coat_001",
    "added_at": "2024-12-02T10:15:00Z"
  },
  {
    "id": 1,
    "user_id": 1,
    "product_id": "jacket_001",
    "added_at": "2024-12-02T10:10:00Z"
  }
]
```

**Пример curl:**
```bash
curl "http://localhost:8000/api/favorites/1"
```

---

### 3.4 Проверить наличие в избранном

**Endpoint:** `GET /api/favorites/{user_id}/check/{product_id}`

**Описание:** Проверяет, находится ли товар в избранном пользователя.

**Path Parameters:**
- `user_id` (integer) - ID пользователя в БД
- `product_id` (string) - ID товара из Google Sheets

**Response:** `200 OK`
```json
{
  "is_favorite": true
}
```

**Пример curl:**
```bash
curl "http://localhost:8000/api/favorites/1/check/jacket_001"
```

---

## 4. Catalog API

Работа с каталогом товаров из Google Sheets.

### 4.1 Получить список категорий

**Endpoint:** `GET /api/catalog/categories`

**Описание:** Возвращает все категории товаров из Google Sheets, отсортированные по `display_order`.

**Response:** `200 OK`
```json
[
  {
    "category_id": "jackets_oversize",
    "category_name": "Куртки оверсайз",
    "display_order": 1,
    "emoji": "🧥"
  },
  {
    "category_id": "coats",
    "category_name": "Пальто",
    "display_order": 2,
    "emoji": "🧥"
  }
]
```

**Кеширование:** 10 минут

**Пример curl:**
```bash
curl "http://localhost:8000/api/catalog/categories"
```

---

### 4.2 Получить товары

**Endpoint:** `GET /api/catalog/products`

**Описание:** Возвращает товары. Можно фильтровать по категории.

**Query Parameters:**
- `category` (string, опционально) - ID категории для фильтрации

**Response без фильтра:** `200 OK`
```json
[
  {
    "product_id": "jacket_001",
    "category": "jackets_oversize",
    "name": "Куртка оверсайз черная",
    "description": "Стильная куртка...",
    "wb_link": "https://www.wildberries.ru/",
    "available_sizes": "XS,S,M,L,XL",
    "collage_url": "https://example.com/collage.jpg",
    "photo_1_url": "https://example.com/photo1.jpg",
    "photo_2_url": "https://example.com/photo2.jpg",
    "photo_3_url": "https://example.com/photo3.jpg",
    "photo_4_url": "https://example.com/photo4.jpg",
    "size_table_id": "outerwear_standard"
  }
]
```

**Response с фильтром:** `200 OK`
```json
[
  {
    "product_id": "jacket_001",
    "category": "jackets_oversize",
    "name": "Куртка оверсайз черная",
    ...
  }
]
```

**Кеширование:** 5 минут

**Пример curl:**
```bash
# Все товары
curl "http://localhost:8000/api/catalog/products"

# Товары категории
curl "http://localhost:8000/api/catalog/products?category=jackets_oversize"
```

---

### 4.3 Получить товар по ID

**Endpoint:** `GET /api/catalog/products/{product_id}`

**Описание:** Возвращает информацию о конкретном товаре.

**Path Parameters:**
- `product_id` (string) - ID товара из Google Sheets

**Response:** `200 OK`
```json
{
  "product_id": "jacket_001",
  "category": "jackets_oversize",
  "name": "Куртка оверсайз черная",
  "description": "Стильная куртка оверсайз из плотной ткани...",
  "wb_link": "https://www.wildberries.ru/",
  "available_sizes": "XS,S,M,L,XL",
  "collage_url": "https://example.com/collage.jpg",
  "photo_1_url": "https://example.com/photo1.jpg",
  "photo_2_url": "https://example.com/photo2.jpg",
  "photo_3_url": "https://example.com/photo3.jpg",
  "photo_4_url": "https://example.com/photo4.jpg",
  "size_table_id": "outerwear_standard"
}
```

**Response:** `404 Not Found`
```json
{
  "detail": "Product not found"
}
```

**Кеширование:** 5 минут

**Пример curl:**
```bash
curl "http://localhost:8000/api/catalog/products/jacket_001"
```

---

### 4.4 Очистить кеш

**Endpoint:** `POST /api/catalog/refresh-cache`

**Описание:** Принудительно очищает кеш Google Sheets (категории, товары, таблицы размеров).

**Response:** `200 OK`
```json
{
  "status": "ok",
  "message": "Cache cleared"
}
```

**Пример curl:**
```bash
curl -X POST "http://localhost:8000/api/catalog/refresh-cache"
```

---

## 5. Size Recommendation API

Подбор размера на основе параметров пользователя.

### 5.1 Рекомендовать размер

**Endpoint:** `POST /api/size/recommend`

**Описание:** Подбирает размер одежды на основе параметров пользователя и таблицы размеров товара.

**Request Body:**
```json
{
  "user_id": 1,
  "product_id": "jacket_001"
}
```

**Параметры:**
- `user_id` (integer) - ID пользователя в БД
- `product_id` (string) - ID товара из Google Sheets

**Response (успешный подбор):** `200 OK`
```json
{
  "success": true,
  "recommended_size": "M",
  "alternative_size": "L",
  "confidence": "high",
  "message": "✅ Рекомендуемый размер: M (также может подойти L)",
  "details": {
    "score": 4,
    "max_possible_score": 4,
    "matched_parameters": ["height", "chest", "waist", "hips"]
  }
}
```

**Response (параметры не указаны):** `200 OK`
```json
{
  "success": false,
  "recommended_size": null,
  "alternative_size": null,
  "confidence": "none",
  "message": "📐 Укажи свои параметры, чтобы получить рекомендацию по размеру",
  "details": {
    "reason": "no_measurements"
  }
}
```

**Response (не удалось подобрать):** `200 OK`
```json
{
  "success": false,
  "recommended_size": null,
  "alternative_size": null,
  "confidence": "none",
  "message": "⚠️ Не удалось подобрать размер. Рекомендуем уточнить у продавца",
  "details": {
    "reason": "no_match"
  }
}
```

**Уровни confidence:**
- `high` - все 4 параметра совпали
- `medium` - 3 параметра совпали
- `low` - 2 или меньше параметров совпали
- `none` - не удалось подобрать

**Пример curl:**
```bash
curl -X POST "http://localhost:8000/api/size/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "product_id": "jacket_001"
  }'
```

---

## 6. Admin API

Административная панель и статистика.

### 6.1 Получить статистику

**Endpoint:** `GET /api/admin/stats`

**Описание:** Возвращает статистику использования бота.

**Response:** `200 OK`
```json
{
  "users": {
    "total": 127,
    "today": 5,
    "week": 23,
    "month": 89,
    "active_week": 67
  },
  "measurements": {
    "count": 85,
    "percent": 66.9
  },
  "favorites": {
    "total": 234,
    "top": [
      {
        "product_id": "jacket_001",
        "count": 45
      },
      {
        "product_id": "coat_001",
        "count": 38
      },
      {
        "product_id": "pants_001",
        "count": 32
      }
    ]
  }
}
```

**Описание полей:**

**users:**
- `total` - Всего пользователей
- `today` - Новых за сегодня
- `week` - Новых за последние 7 дней
- `month` - Новых за последние 30 дней
- `active_week` - Активных за последние 7 дней

**measurements:**
- `count` - Пользователей с указанными параметрами
- `percent` - Процент от общего числа

**favorites:**
- `total` - Всего добавлений в избранное
- `top` - ТОП-5 избранных товаров

**Пример curl:**
```bash
curl "http://localhost:8000/api/admin/stats"
```

---

## 7. Общие endpoints

### 7.1 Root

**Endpoint:** `GET /`

**Описание:** Информация об API.

**Response:** `200 OK`
```json
{
  "message": "Fitting Bot API",
  "version": "1.0.0",
  "docs": "/docs"
}
```

**Пример curl:**
```bash
curl "http://localhost:8000/"
```

---

### 7.2 Health Check

**Endpoint:** `GET /health`

**Описание:** Проверка работоспособности API.

**Response:** `200 OK`
```json
{
  "status": "healthy"
}
```

**Пример curl:**
```bash
curl "http://localhost:8000/health"
```

---

## Примеры использования

### Сценарий 1: Регистрация нового пользователя

```bash
# 1. Регистрация
curl -X POST "http://localhost:8000/api/users/register" \
  -H "Content-Type: application/json" \
  -d '{
    "tg_id": 123456789,
    "username": "john_doe",
    "first_name": "John"
  }'

# Response: { "id": 1, "tg_id": 123456789, ... }
```

### Сценарий 2: Сохранение параметров и подбор размера

```bash
# 1. Сохранить параметры
curl -X POST "http://localhost:8000/api/measurements/1" \
  -H "Content-Type: application/json" \
  -d '{
    "height": 165,
    "chest": 85,
    "waist": 65,
    "hips": 95
  }'

# 2. Подобрать размер для товара
curl -X POST "http://localhost:8000/api/size/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "product_id": "jacket_001"
  }'

# Response: { "success": true, "recommended_size": "M", ... }
```

### Сценарий 3: Работа с избранным

```bash
# 1. Добавить в избранное
curl -X POST "http://localhost:8000/api/favorites/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "product_id": "jacket_001"
  }'

# 2. Проверить наличие
curl "http://localhost:8000/api/favorites/1/check/jacket_001"
# Response: { "is_favorite": true }

# 3. Получить весь список
curl "http://localhost:8000/api/favorites/1"

# 4. Удалить
curl -X DELETE "http://localhost:8000/api/favorites/1/jacket_001"
```

### Сценарий 4: Просмотр каталога

```bash
# 1. Получить категории
curl "http://localhost:8000/api/catalog/categories"

# 2. Получить товары категории
curl "http://localhost:8000/api/catalog/products?category=jackets_oversize"

# 3. Получить конкретный товар
curl "http://localhost:8000/api/catalog/products/jacket_001"
```

---

## Обработка ошибок

### Валидация данных (422)

```json
{
  "detail": [
    {
      "loc": ["body", "height"],
      "msg": "ensure this value is greater than or equal to 140",
      "type": "value_error.number.not_ge"
    }
  ]
}
```

### Ресурс не найден (404)

```json
{
  "detail": "User not found"
}
```

### Внутренняя ошибка (500)

```json
{
  "detail": "Internal server error"
}
```

---

## Swagger UI

Интерактивная документация доступна по адресу:

**http://localhost:8000/docs**

Там можно:
- Посмотреть все endpoints
- Протестировать запросы
- Посмотреть схемы данных

---

## Postman Collection

Для удобства тестирования можно импортировать все endpoints в Postman:

1. Откройте Postman
2. Import → Link
3. Вставьте: `http://localhost:8000/openapi.json`
4. Все endpoints будут импортированы автоматически

---

## Кеширование

API использует кеширование для данных из Google Sheets:

| Тип данных | TTL | Endpoint для сброса |
|------------|-----|---------------------|
| Categories | 10 мин | POST /api/catalog/refresh-cache |
| Products | 5 мин | POST /api/catalog/refresh-cache |
| Size Tables | 30 мин | POST /api/catalog/refresh-cache |

При изменении данных в Google Sheets нужно подождать истечения TTL или вручную очистить кеш.

---

## Rate Limiting

На текущий момент rate limiting не реализован. Будет добавлен в будущих версиях.

---

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker-compose logs api`
2. Убедитесь, что БД подключена: `curl http://localhost:8000/health`
3. Проверьте Swagger UI: http://localhost:8000/docs
