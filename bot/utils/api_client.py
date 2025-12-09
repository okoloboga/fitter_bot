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
    async def save_measurements(self, user_tg_id: int, **measurements) -> Optional[Dict]:
        """Сохранить параметры пользователя (поддерживает частичное обновление)"""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/measurements/{user_tg_id}",
                json=measurements
            ) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to save measurements: {response.status} {await response.text()}")
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

    # Try-on endpoints
    async def check_tryon_limit(self, user_tg_id: int) -> Optional[Dict]:
        """Проверить лимит примерок"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tryon/check-limit/{user_tg_id}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error checking try-on limit: {e}")
            return None

    async def get_user_photos(self, user_tg_id: int) -> Optional[Dict]:
        """Получить фото пользователя"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/photos/{user_tg_id}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting user photos: {e}")
            return None

    async def upload_photo(self, tg_id: int, file_id: str, file_path: str, consent_given: bool) -> Optional[Dict]:
        """Загрузить фото"""
        try:
            session = await self._get_session()
            payload = {
                "tg_id": tg_id,
                "file_id": file_id,
                "file_path": file_path,
                "consent_given": consent_given
            }
            async with session.post(f"{self.base_url}/api/photos/upload", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to upload photo: {response.status} {await response.text()}")
                return None
        except Exception as e:
            logger.error(f"Error uploading photo: {e}")
            return None

    async def delete_photo(self, photo_id: int) -> bool:
        """Удалить фото"""
        try:
            session = await self._get_session()
            async with session.delete(f"{self.base_url}/api/photos/{photo_id}") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error deleting photo: {e}")
            return False

    async def create_tryon(self, tg_id: int, product_id: str, photo_id: int) -> Optional[Dict]:
        """Создать запись о примерке"""
        try:
            session = await self._get_session()
            payload = {
                "tg_id": tg_id,
                "product_id": product_id,
                "user_photo_id": photo_id
            }
            async with session.post(f"{self.base_url}/api/tryon/create", json=payload) as response:
                if response.status == 200:
                    return await response.json()
                logger.error(f"Failed to create try-on: {response.status} {await response.text()}")
                return None
        except Exception as e:
            logger.error(f"Error creating try-on: {e}")
            return None
    
    async def update_tryon(self, tryon_id: int, status: str, result_file_path: Optional[str] = None, generation_time: Optional[int] = None) -> bool:
        """Обновить запись о примерке"""
        try:
            session = await self._get_session()
            payload = {"status": status}
            if result_file_path:
                payload["result_file_path"] = result_file_path
            if generation_time:
                payload["generation_time"] = generation_time
            async with session.put(f"{self.base_url}/api/tryon/{tryon_id}", json=payload) as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error updating try-on: {e}")
            return False

    async def get_tryon_history(self, user_tg_id: int) -> Optional[Dict]:
        """Получить историю примерок"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tryon/history/{user_tg_id}") as response:
                if response.status == 200:
                    return await response.json()
                return None
        except Exception as e:
            logger.error(f"Error getting try-on history: {e}")
            return None

    async def has_tryon_history(self, user_tg_id: int) -> bool:
        """Проверить, есть ли у пользователя история примерок"""
        try:
            history_result = await self.get_tryon_history(user_tg_id)
            if history_result and "history" in history_result:
                return len(history_result["history"]) > 0
            return False
        except Exception as e:
            logger.error(f"Error checking try-on history: {e}")
            return False

    async def delete_tryon(self, tryon_id: int) -> bool:
        """Удалить примерку"""
        try:
            session = await self._get_session()
            async with session.delete(f"{self.base_url}/api/tryon/{tryon_id}") as response:
                return response.status == 200
        except Exception as e:
            logger.error(f"Error deleting try-on: {e}")
            return False


# Singleton instance
api_client = APIClient()


# Вспомогательная функция для простых API запросов
async def api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
    """
    Универсальная функция для API запросов

    Args:
        method: HTTP метод (GET, POST, PUT, DELETE)
        endpoint: API endpoint (например "/photos/upload")
        data: Данные для отправки (для POST/PUT)

    Returns:
        Dict с ответом от API
    """
    try:
        session = await api_client._get_session()
        url = f"{api_client.base_url}/api{endpoint}"

        if method.upper() == "GET":
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {method} {endpoint} - {response.status}")
                    return {"success": False, "error": f"HTTP {response.status}"}

        elif method.upper() == "POST":
            async with session.post(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {method} {endpoint} - {response.status}")
                    return {"success": False, "error": f"HTTP {response.status}"}

        elif method.upper() == "PUT":
            async with session.put(url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {method} {endpoint} - {response.status}")
                    return {"success": False, "error": f"HTTP {response.status}"}

        elif method.upper() == "DELETE":
            async with session.delete(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API request failed: {method} {endpoint} - {response.status}")
                    return {"success": False, "error": f"HTTP {response.status}"}

        else:
            logger.error(f"Unsupported HTTP method: {method}")
            return {"success": False, "error": f"Unsupported method: {method}"}

    except Exception as e:
        logger.error(f"API request error: {method} {endpoint} - {e}")
        return {"success": False, "error": str(e)}
