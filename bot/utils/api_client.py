"""
HTTP клиент для взаимодействия с FastAPI
"""
import aiohttp
import logging
import os
import asyncio
from functools import wraps
from typing import Optional, Dict, List, Any, Callable, Coroutine

logger = logging.getLogger(__name__)

API_URL = os.getenv("API_URL", "http://localhost:8000")

# --- Decorator for Error Handling ---

def _handle_api_exceptions(default_return: Any = None):
    """
    Декоратор для обработки исключений при запросах к API.
    Ловит сетевые ошибки и плохие статусы HTTP.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(self: "APIClient", *args, **kwargs) -> Any:
            method_name = func.__name__
            try:
                session = await self._get_session()
                response: Optional[aiohttp.ClientResponse] = await func(self, session, *args, **kwargs)

                # Успешные статусы (2xx)
                if response and 200 <= response.status < 300:
                    # Если функция должна вернуть bool, успешный запрос означает True
                    if func.__annotations__.get('return') == bool:
                        return True
                    
                    if response.content_type == 'application/json':
                        return await response.json()
                    
                    # Для запросов без тела (например, 204 No Content)
                    if response.status == 204:
                        return None
                        
                    return await response.text()

                # Обработка не-успешных статусов
                error_body = await response.text() if response else "No response object"
                status = response.status if response else "N/A"
                logger.error(
                    f"API Error in {method_name}: "
                    f"status={status}, "
                    f"body='{error_body[:200]}...'"
                )
                return default_return

            except aiohttp.ClientError as e:
                logger.error(f"Network Error in {method_name}: {type(e).__name__} - {e}")
                return default_return
            except asyncio.TimeoutError:
                logger.error(f"Timeout Error in {method_name}")
                return default_return
            except Exception as e:
                logger.error(f"Unexpected Error in {method_name}: {type(e).__name__} - {e}", exc_info=True)
                return default_return
        return wrapper
    return decorator


class APIClient:
    """Клиент для работы с FastAPI backend"""

    def __init__(self, base_url: str = API_URL):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Получить или создать сессию"""
        if self.session is None or self.session.closed:
            # Устанавливаем разумный таймаут для всех запросов
            timeout = aiohttp.ClientTimeout(total=15)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session

    async def close(self):
        """Закрыть сессию"""
        if self.session and not self.session.closed:
            await self.session.close()

    # --- Users endpoints ---

    @_handle_api_exceptions(default_return=None)
    async def register_user(self, session: aiohttp.ClientSession, tg_id: int, username: Optional[str], first_name: Optional[str]) -> Optional[Dict]:
        return await session.post(
            f"{self.base_url}/api/users/register",
            json={"tg_id": tg_id, "username": username, "first_name": first_name}
        )

    @_handle_api_exceptions(default_return=None)
    async def get_user_by_tg_id(self, session: aiohttp.ClientSession, tg_id: int) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/users/by-tg-id/{tg_id}")

    # --- Measurements endpoints ---

    @_handle_api_exceptions(default_return=None)
    async def save_measurements(self, session: aiohttp.ClientSession, user_tg_id: int, **measurements) -> Optional[Dict]:
        return await session.post(
            f"{self.base_url}/api/measurements/{user_tg_id}",
            json=measurements
        )

    @_handle_api_exceptions(default_return=None)
    async def get_measurements(self, session: aiohttp.ClientSession, user_tg_id: int) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/measurements/{user_tg_id}")

    # --- Favorites endpoints ---

    @_handle_api_exceptions(default_return=None)
    async def add_to_favorites(self, session: aiohttp.ClientSession, user_id: int, product_id: str) -> Optional[Dict]:
        return await session.post(
            f"{self.base_url}/api/favorites/",
            json={"user_id": user_id, "product_id": product_id}
        )

    @_handle_api_exceptions(default_return=False)
    async def remove_from_favorites(self, session: aiohttp.ClientSession, user_tg_id: int, product_id: str) -> bool:
        return await session.delete(f"{self.base_url}/api/favorites/{user_tg_id}/{product_id}")

    @_handle_api_exceptions(default_return=[])
    async def get_favorites(self, session: aiohttp.ClientSession, user_tg_id: int) -> List[Dict]:
        return await session.get(f"{self.base_url}/api/favorites/{user_tg_id}")

    @_handle_api_exceptions(default_return=False)
    async def check_favorite(self, session: aiohttp.ClientSession, user_tg_id: int, product_id: str) -> bool:
        response = await session.get(f"{self.base_url}/api/favorites/{user_tg_id}/check/{product_id}")
        data = await response.json()
        return data.get("is_favorite", False)

    # --- Catalog endpoints ---

    @_handle_api_exceptions(default_return=[])
    async def get_categories(self, session: aiohttp.ClientSession) -> List[Dict]:
        return await session.get(f"{self.base_url}/api/catalog/categories")

    @_handle_api_exceptions(default_return=[])
    async def get_products_by_category(self, session: aiohttp.ClientSession, category: str) -> List[Dict]:
        return await session.get(f"{self.base_url}/api/catalog/products?category={category}")

    @_handle_api_exceptions(default_return=None)
    async def get_product_by_id(self, session: aiohttp.ClientSession, product_id: str) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/catalog/products/{product_id}")

    # --- Size recommendation ---

    @_handle_api_exceptions(default_return=None)
    async def recommend_size(self, session: aiohttp.ClientSession, user_id: int, product_id: str) -> Optional[Dict]:
        return await session.post(
            f"{self.base_url}/api/size/recommend",
            json={"user_id": user_id, "product_id": product_id}
        )

    # --- Admin endpoints ---

    @_handle_api_exceptions(default_return=None)
    async def get_admin_stats(self, session: aiohttp.ClientSession) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/admin/stats")

    # --- Try-on endpoints ---

    @_handle_api_exceptions(default_return=None)
    async def check_tryon_limit(self, session: aiohttp.ClientSession, user_tg_id: int) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/tryon/check-limit/{user_tg_id}")

    @_handle_api_exceptions(default_return=None)
    async def get_user_photos(self, session: aiohttp.ClientSession, user_tg_id: int) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/photos/{user_tg_id}")

    @_handle_api_exceptions(default_return=None)
    async def upload_photo(self, session: aiohttp.ClientSession, tg_id: int, file_id: str, file_path: str, consent_given: bool) -> Optional[Dict]:
        data = aiohttp.FormData()
        data.add_field('user_id', str(tg_id))
        data.add_field('file_id', file_id)
        data.add_field('consent_given', str(consent_given).lower())
        
        try:
            file_name = os.path.basename(file_path)
            # Открываем файл для чтения в бинарном режиме
            # и передаем его в FormData
            data.add_field('file',
                           open(file_path, 'rb'),
                           filename=file_name,
                           content_type='application/octet-stream')
        except FileNotFoundError:
            logger.error(f"File not found at path for upload: {file_path}")
            return None
        
        # Увеличиваем таймаут специально для этого запроса, т.к. загрузка файла может быть долгой
        timeout = aiohttp.ClientTimeout(total=60)
        
        return await session.post(
            f"{self.base_url}/api/photos/upload",
            data=data,
            timeout=timeout
        )

    @_handle_api_exceptions(default_return=False)
    async def delete_photo(self, session: aiohttp.ClientSession, photo_id: int) -> bool:
        return await session.delete(f"{self.base_url}/api/photos/{photo_id}")

    @_handle_api_exceptions(default_return=None)
    async def create_tryon(self, session: aiohttp.ClientSession, tg_id: int, product_id: str, photo_id: int) -> Optional[Dict]:
        payload = {
            "user_id": tg_id,
            "product_id": product_id,
            "user_photo_id": photo_id
        }
        return await session.post(f"{self.base_url}/api/tryon/create", json=payload)
    
    @_handle_api_exceptions(default_return=False)
    async def update_tryon(self, session: aiohttp.ClientSession, tryon_id: int, status: str, result_file_path: Optional[str] = None, generation_time: Optional[int] = None) -> bool:
        payload = {"status": status}
        if result_file_path:
            payload["result_file_path"] = result_file_path
        if generation_time:
            payload["generation_time"] = generation_time
        return await session.put(f"{self.base_url}/api/tryon/{tryon_id}", json=payload)

    @_handle_api_exceptions(default_return=None)
    async def get_tryon_history(self, session: aiohttp.ClientSession, user_tg_id: int) -> Optional[Dict]:
        return await session.get(f"{self.base_url}/api/tryon/history/{user_tg_id}")

    async def has_tryon_history(self, user_tg_id: int) -> bool:
        """Проверить, есть ли у пользователя история примерок"""
        # Эта функция вызывает другую, уже обернутую, поэтому здесь декоратор не нужен
        history_result = await self.get_tryon_history(user_tg_id)
        if history_result and "history" in history_result:
            return len(history_result["history"]) > 0
        return False

    @_handle_api_exceptions(default_return=False)
    async def delete_tryon(self, session: aiohttp.ClientSession, tryon_id: int) -> bool:
        return await session.delete(f"{self.base_url}/api/tryon/{tryon_id}")


# Singleton instance
api_client = APIClient()

# Generic request function is removed as it's better to have explicit client methods