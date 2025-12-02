"""
Моковые данные категорий товаров
"""

CATEGORIES = [
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
    },
    {
        "category_id": "puffers",
        "category_name": "Пуховики",
        "display_order": 3,
        "emoji": "🧥"
    },
    {
        "category_id": "raincoats",
        "category_name": "Плащи",
        "display_order": 4,
        "emoji": "🧥"
    },
    {
        "category_id": "bombers",
        "category_name": "Бомберы",
        "display_order": 5,
        "emoji": "🧥"
    },
    {
        "category_id": "vests",
        "category_name": "Жилеты",
        "display_order": 6,
        "emoji": "🧥"
    },
    {
        "category_id": "windbreakers",
        "category_name": "Ветровки",
        "display_order": 7,
        "emoji": "🧥"
    },
    {
        "category_id": "parkas",
        "category_name": "Парки",
        "display_order": 8,
        "emoji": "🧥"
    },
    {
        "category_id": "pants",
        "category_name": "Штаны",
        "display_order": 9,
        "emoji": "👖"
    }
]


def get_categories():
    """Получить список всех категорий"""
    return sorted(CATEGORIES, key=lambda x: x['display_order'])


def get_category_by_id(category_id: str):
    """Получить категорию по ID"""
    for category in CATEGORIES:
        if category['category_id'] == category_id:
            return category
    return None
