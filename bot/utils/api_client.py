"""
HTTP клиент для взаимодействия с FastAPI
"""
import aiohttp
import logging
import os
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://localhost:8000")


class APIClient:
    """Клиент для работы с FastAPI backend"""

    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать сессию"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def close(self):
        """Закрыть сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

    # Users endpoints
    async def register_user(self, tg_id: int, username: Optional[str], first_name: Optional[str]) -> Optional[Dict]:
        """Регистрация пользователя"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/users/register",
                json={"tg_id": tg_id, "username": username, "first_name": first_name}
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to register user: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error registering user: {e}")
            return None

    async def get_user_by_tg_id(self, tg_id: int) -> Optional[Dict]:
        """Получить пользователя по Telegram ID"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/users/by-tg-id/{tg_id}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    # Measurements endpoints
    async def save_measurements(self, user_tg_id: int, height: int, chest: int, waist: int, hips: int) -> Optional[Dict]:
        """Сохранить параметры пользователя"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/measurements/{user_tg_id}",
                json={"height": height, "chest": chest, "waist": waist, "hips": hips}
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to save measurements: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error saving measurements: {e}")
            return None

    async def get_measurements(self, user_tg_id: int) -> Optional[Dict]:
        """Получить параметры пользователя"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/measurements/{user_tg_id}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting measurements: {e}")
            return None

    # Favorites endpoints
    async def add_to_favorites(self, user_tg_id: int, product_id: str) -> Optional[Dict]:
        """Добавить товар в избранное"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/favorites/",
                json={"user_id": user_tg_id, "product_id": product_id}
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to add to favorites: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error adding to favorites: {e}")
            return None

    async def remove_from_favorites(self, user_tg_id: int, product_id: str) -> bool:
        """Удалить товар из избранного"""
        try:
            session = await self._get_session()
            async with session.delete(f"{self.base_url}/api/favorites/{user_tg_id}/{product_id}") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error removing from favorites: {e}")
            return False

    async def get_favorites(self, user_tg_id: int) -> List[Dict]:
        """Получить список избранного"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/favorites/{user_tg_id}") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting favorites: {e}")
            return []

    async def check_favorite(self, user_tg_id: int, product_id: str) -> bool:
        """Проверить, в избранном ли товар"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/favorites/{user_tg_id}/check/{product_id}") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("is_favorite", False)
                return False
        except Exception as e:
            logger.error(f"Error checking favorite: {e}")
            return False

    # Catalog endpoints
    async def get_categories(self) -> List[Dict]:
        """Получить список категорий"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/catalog/categories") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return []

    async def get_products_by_category(self, category: str) -> List[Dict]:
        """Получить товары категории"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/catalog/products?category={category}") as response:
                if response.status == 200:
                    return await response.json()
                return []
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []

    async def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Получить товар по ID"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/catalog/products/{product_id}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting product: {e}")
            return None

    # Size recommendation
    async def recommend_size(self, user_id: int, product_id: str) -> Optional[Dict]:
        """Получить рекомендацию размера"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/size/recommend",
                json={"user_id": user_id, "product_id": product_id}
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to get size recommendation: {response.status}")
                return None
        except Exception as e:
            logger.error(f"Error getting size recommendation: {e}")
            return None

    # Admin endpoints
    async def get_admin_stats(self) -> Optional[Dict]:
        """Получить статистику"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/admin/stats") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return None


# Singleton instance
api_client = APIClient()
