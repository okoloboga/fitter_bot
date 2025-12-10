# Исправление проблемы "API not ready" при старте бота

## Проблема

При запуске бота через Docker Compose:
```
Cannot connect to host api:8000 ssl:default [Connect call failed ('172.19.0.4', 8000)]
No categories found. Skipping photo preload.
```

**Причина:** Race condition - бот пытается предзагрузить фото до того, как API готов принимать запросы.

---

## Решение

### 1. ✅ Добавлен healthcheck для API (docker-compose.yml)

```yaml
api:
  healthcheck:
    test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:8000/health"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s
```

### 2. ✅ Изменен depends_on для бота

```yaml
bot:
  depends_on:
    api:
      condition: service_healthy  # Было: service_started
```

### 3. ✅ Добавлен wget в Dockerfile

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    && rm -rf /var/lib/apt/lists/*
```

### 4. ✅ Добавлена retry логика в main.py

```python
async def wait_for_api_ready(max_retries: int = 10, delay: int = 3):
    """Ожидание готовности API сервера"""
    # Попытки подключения к API с задержкой
```

### 5. ✅ Добавлен volume для storage

```yaml
volumes:
  - storage_data:/app/storage  # Фото не теряются при перезапуске
```

---

## Применение изменений

### 1. Пересобрать контейнеры

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 2. Проверить логи

```bash
# Логи API (должен стартовать первым)
docker-compose logs -f api

# Логи бота (должен дождаться API)
docker-compose logs -f bot
```

### 3. Ожидаемый результат

```
api    | INFO - Starting FastAPI application...
api    | INFO - Database initialized
bot    | INFO - Waiting for API to be ready...
bot    | INFO - ✅ API is ready!
bot    | INFO - Starting product photos preload...
bot    | INFO - Found 25 products across 5 categories
bot    | INFO - Downloaded: 150
bot    | INFO - Photo preload completed!
```

---

## Как работает

1. **API запускается** и начинает healthcheck каждые 10 секунд
2. После **5 успешных проверок** API помечается как `healthy`
3. **Только тогда** Docker Compose запускает бот
4. Бот **дополнительно** делает 10 попыток подключения (retry logic)
5. После подключения начинается **предзагрузка фото**

---

## Troubleshooting

### Проблема: API не проходит healthcheck

```bash
# Проверить статус
docker-compose ps

# Если api unhealthy, проверить логи
docker-compose logs api
```

**Решение:**
- Увеличить `start_period` в healthcheck (сейчас 30s)
- Проверить что эндпоинт `/health` работает: `curl http://localhost:8000/health`

### Проблема: Бот все еще не может подключиться

```bash
# Проверить логи бота
docker-compose logs bot | grep "API not ready"
```

**Решение:**
- Увеличить `max_retries` в функции `wait_for_api_ready()` (сейчас 10)
- Увеличить `delay` между попытками (сейчас 3 секунды)

---

## Дополнительные настройки

### Изменить интервал фонового обновления фото

В `.env`:
```bash
PHOTO_UPDATE_INTERVAL_MINUTES=30  # По умолчанию 30 минут
```

### Проверить хранилище фото

```bash
# Войти в контейнер
docker exec -it fitting_bot bash

# Проверить фото
ls -lh /app/storage/product_photos/
du -sh /app/storage/product_photos/
```

---

## Changelog

**2025-12-10:**
- ✅ Исправлена проблема race condition при старте
- ✅ Добавлен healthcheck для API
- ✅ Добавлена retry логика в бот
- ✅ Добавлен persistent volume для storage
