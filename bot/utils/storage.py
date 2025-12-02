"""
Хранилище данных в памяти для этапа 0
На этапе 1 будет заменено на работу с PostgreSQL
"""

# Хранилище параметров пользователей
# Структура: {user_id: {"height": 165, "chest": 85, "waist": 65, "hips": 95}}
user_measurements = {}

# Хранилище избранного
# Структура: {user_id: [product_id_1, product_id_2, ...]}
user_favorites = {}


def save_measurements(user_id: int, height: int, chest: int, waist: int, hips: int):
    """Сохранить параметры пользователя"""
    user_measurements[user_id] = {
        "height": height,
        "chest": chest,
        "waist": waist,
        "hips": hips
    }


def get_measurements(user_id: int):
    """Получить параметры пользователя"""
    return user_measurements.get(user_id)


def update_measurement(user_id: int, param: str, value: int):
    """Обновить конкретный параметр"""
    if user_id not in user_measurements:
        user_measurements[user_id] = {}
    user_measurements[user_id][param] = value


def add_to_favorites(user_id: int, product_id: str):
    """Добавить товар в избранное"""
    if user_id not in user_favorites:
        user_favorites[user_id] = []

    if product_id not in user_favorites[user_id]:
        user_favorites[user_id].append(product_id)


def remove_from_favorites(user_id: int, product_id: str):
    """Удалить товар из избранного"""
    if user_id in user_favorites and product_id in user_favorites[user_id]:
        user_favorites[user_id].remove(product_id)


def get_favorites(user_id: int):
    """Получить список избранного пользователя"""
    return user_favorites.get(user_id, [])


def is_favorite(user_id: int, product_id: str):
    """Проверить, находится ли товар в избранном"""
    return user_id in user_favorites and product_id in user_favorites[user_id]
