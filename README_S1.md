# Fitting Bot - Этап 1 (Каталог и подбор размеров)

Полнофункциональный Telegram-бот с FastAPI backend, PostgreSQL, Google Sheets и реальным алгоритмом подбора размеров.

## Что реализовано в Этапе 1

✅ **FastAPI Backend** - RESTful API для бизнес-логики
✅ **PostgreSQL** - Хранение пользователей, параметров, избранного
✅ **Google Sheets Integration** - Чтение каталога товаров из таблицы
✅ **Реальный алгоритм подбора размеров** - На основе таблиц размеров
✅ **Кеширование** - Данные из Google Sheets кешируются для производительности
✅ **Миграции Alembic** - Управление схемой БД
✅ **HTTP клиент** - Бот общается с API

## Архитектура

```
Telegram Bot (Aiogram) → FastAPI Backend → PostgreSQL
                              ↓
                        Google Sheets API
```

**Сервисы:**
- `api` - FastAPI приложение (порт 8000)
- `bot` - Telegram бот
- `postgres` - База данных
- `redis` - FSM хранилище

## Быстрый старт

### 1. Настройка окружения

```bash
# Копировать конфигурацию
cp .env.example .env

# Отредактировать .env - добавить:
# - TELEGRAM_BOT_TOKEN
# - GOOGLE_SHEETS_SPREADSHEET_ID
```

### 2. Настройка Google Sheets

Следуйте инструкции: [docs/GOOGLE_SHEETS_SETUP.md](docs/GOOGLE_SHEETS_SETUP.md)

**Кратко:**
1. Создайте проект в Google Cloud Console
2. Включите Google Sheets API и Google Drive API
3. Создайте Service Account и скачайте `credentials.json`
4. Поместите файл в `config/credentials.json`
5. Создайте таблицу с 3 листами: Categories, Products, Size_Tables
6. Предоставьте доступ Service Account email к таблице

### 3. Создание таблицы

Структура Google Sheets должна содержать:

**Лист "Categories":**
- category_id, category_name, display_order, emoji

**Лист "Products":**
- product_id, category, name, description, wb_link, available_sizes
- collage_url, photo_1_url, photo_2_url, photo_3_url, photo_4_url
- is_active, size_table_id

**Лист "Size_Tables":**
- table_id, size, height_min/max, chest_min/max, waist_min/max, hips_min/max

Пример структуры см. в [docs/S1/S1.md](docs/S1/S1.md)

### 4. Запуск через Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Логи API
docker-compose logs -f api

# Логи бота
docker-compose logs -f bot
```

### 5. Применение миграций БД

```bash
# Внутри контейнера API
docker-compose exec api alembic upgrade head

# Или локально (если установлены зависимости)
alembic upgrade head
```

### 6. Проверка работоспособности

**API:**
```bash
curl http://localhost:8000/health
```

**Swagger документация:**
http://localhost:8000/docs

**Telegram Bot:**
Отправьте `/start` боту в Telegram

## Структура проекта

```
fitting_bot/
├── api/                     # FastAPI приложение
│   ├── main.py             # Главный файл API
│   ├── database.py         # Подключение к БД
│   ├── models.py           # SQLAlchemy модели
│   ├── schemas.py          # Pydantic схемы
│   ├── routers/            # API endpoints
│   │   ├── users.py
│   │   ├── measurements.py
│   │   ├── favorites.py
│   │   ├── catalog.py
│   │   ├── size_recommend.py
│   │   └── admin.py
│   └── services/           # Бизнес-логика
│       ├── sheets.py       # Google Sheets сервис
│       └── size_matcher.py # Алгоритм подбора размеров
├── bot/                    # Telegram бот
│   ├── handlers/           # Обработчики (используют API)
│   ├── keyboards/          # Клавиатуры
│   ├── states/             # FSM состояния
│   ├── mock_data/          # Моковые данные (fallback)
│   └── utils/
│       ├── storage.py      # (deprecated в S1)
│       └── api_client.py   # HTTP клиент для API
├── config/                 # Конфигурация
│   └── credentials.json    # Google Sheets credentials
├── migrations/             # Alembic миграции
├── docs/                   # Документация
│   ├── S0/S0.md
│   ├── S1/S1.md
│   ├── MAIN.md
│   └── GOOGLE_SHEETS_SETUP.md
├── docker-compose.yml
├── alembic.ini
└── requirements.txt
```

## API Endpoints

### Users
- `POST /api/users/register` - Регистрация пользователя
- `GET /api/users/{user_id}` - Получить пользователя
- `GET /api/users/by-tg-id/{tg_id}` - По Telegram ID

### Measurements
- `POST /api/measurements/{user_id}` - Сохранить параметры
- `GET /api/measurements/{user_id}` - Получить параметры

### Favorites
- `POST /api/favorites/` - Добавить в избранное
- `DELETE /api/favorites/{user_id}/{product_id}` - Удалить
- `GET /api/favorites/{user_id}` - Список избранного

### Catalog
- `GET /api/catalog/categories` - Список категорий
- `GET /api/catalog/products?category={id}` - Товары категории
- `GET /api/catalog/products/{product_id}` - Товар по ID

### Size Recommendation
- `POST /api/size/recommend` - Подобрать размер

### Admin
- `GET /api/admin/stats` - Статистика

## Алгоритм подбора размеров

Система подбирает размер на основе 4 параметров:
- Рост (height)
- Обхват груди (chest)
- Обхват талии (waist)
- Обхват бедер (hips)

**Логика:**
1. Загружается таблица размеров для товара
2. Для каждого размера проверяется попадание параметров в диапазоны
3. Считается score - количество совпадений
4. Размер с максимальным score рекомендуется

**Уровни confidence:**
- `high` - все 4 параметра совпали
- `medium` - 3 параметра совпали
- `low` - 2 или меньше параметров

## Кеширование

**TTL (время жизни кеша):**
- Categories: 10 минут
- Products: 5 минут
- Size_Tables: 30 минут

**Очистка кеша:**
```bash
curl -X POST http://localhost:8000/api/catalog/refresh-cache
```

## Fallback на моковые данные

Если Google Sheets недоступен, система автоматически использует моковые данные из `bot/mock_data/`.

Это полезно для:
- Разработки без Google Sheets
- Тестирования
- Демонстрации функционала

## Локальный запуск (без Docker)

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск PostgreSQL и Redis
# (должны быть установлены локально)

# Применение миграций
alembic upgrade head

# Запуск API
uvicorn api.main:app --reload --port 8000

# Запуск бота (в другом терминале)
python main.py
```

## Миграции БД

```bash
# Создать новую миграцию
alembic revision --autogenerate -m "description"

# Применить миграции
alembic upgrade head

# Откатить миграцию
alembic downgrade -1

# Посмотреть историю
alembic history
```

## Troubleshooting

### API не запускается
```bash
# Проверить логи
docker-compose logs api

# Проверить подключение к БД
docker-compose exec api python -c "from api.database import engine; import asyncio; asyncio.run(engine.connect())"
```

### Google Sheets не работает
1. Проверьте `config/credentials.json`
2. Убедитесь, что Service Account имеет доступ к таблице
3. Проверьте GOOGLE_SHEETS_SPREADSHEET_ID в .env
4. См. подробную инструкцию: `docs/GOOGLE_SHEETS_SETUP.md`

### Бот не подключается к API
```bash
# Проверьте API_URL в .env
API_URL=http://api:8000

# Проверьте, что API запущен
curl http://localhost:8000/health
```

### База данных не создается
```bash
# Применить миграции
docker-compose exec api alembic upgrade head

# Или создать таблицы напрямую (не рекомендуется)
docker-compose exec api python -c "from api.database import init_db; import asyncio; asyncio.run(init_db())"
```

## Мониторинг

**Логи:**
```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f api
docker-compose logs -f bot
```

**Статистика:**
- Через бота: `/admin_stats`
- Через API: `GET /api/admin/stats`

## Следующий этап: S2

На этапе 2 будет добавлено:
- Загрузка фото пользователя
- AI-валидация фото
- Интеграция с Gemini API
- Генерация примерок одежды
- История примерок

## Полезные ссылки

- [Документация FastAPI](https://fastapi.tiangolo.com/)
- [Документация Aiogram](https://docs.aiogram.dev/)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [Alembic документация](https://alembic.sqlalchemy.org/)

## Поддержка

См. техническую документацию:
- `docs/S1/S1.md` - Полное ТЗ этапа 1
- `docs/MAIN.md` - Общее ТЗ проекта
- `docs/GOOGLE_SHEETS_SETUP.md` - Настройка Google Sheets
