"""
Сервис предзагрузки и оптимизации фото товаров
"""
import asyncio
import io
import os
import logging
from pathlib import Path
from typing import Optional, Dict, List
import aiohttp
from PIL import Image

logger = logging.getLogger(__name__)

# Константы оптимизации (как в image_processor.py)
MAX_SIZE = (1280, 1280)
JPEG_QUALITY = 85

# Директория для хранения оптимизированных фото товаров
PRODUCT_PHOTOS_DIR = Path("storage/product_photos")


class PhotoPreloader:
    """Сервис для предзагрузки и оптимизации фото товаров"""

    def __init__(self):
        self.photos_dir = PRODUCT_PHOTOS_DIR
        self.photos_dir.mkdir(parents=True, exist_ok=True)
        # Маппинг: (product_id, photo_type) -> путь к файлу
        self.photo_map: Dict[tuple, Path] = {}
        logger.info(f"PhotoPreloader initialized. Storage: {self.photos_dir.absolute()}")

    def _get_photo_filename(self, product_id: str, photo_type: str) -> str:
        """
        Генерирует имя файла для фото товара

        Args:
            product_id: ID товара
            photo_type: Тип фото (collage, 1, 2, 3, 4, 5, 6)

        Returns:
            Имя файла (например: "12345_collage.jpg")
        """
        return f"{product_id}_{photo_type}.jpg"

    def _get_photo_path(self, product_id: str, photo_type: str) -> Path:
        """Получить полный путь к файлу фото"""
        return self.photos_dir / self._get_photo_filename(product_id, photo_type)

    async def _download_and_optimize(self, url: str, output_path: Path) -> bool:
        """
        Скачать и оптимизировать изображение

        Args:
            url: URL исходного изображения
            output_path: Путь для сохранения оптимизированного файла

        Returns:
            True если успешно, False при ошибке
        """
        if not url or not isinstance(url, str) or not url.strip():
            logger.warning(f"Invalid URL: {repr(url)}")
            return False

        try:
            # Скачиваем изображение
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status != 200:
                        logger.error(f"Failed to download {url}. Status: {response.status}")
                        return False
                    image_data = await response.read()

            # Оптимизируем
            with Image.open(io.BytesIO(image_data)) as img:
                # Конвертируем в RGB если есть альфа-канал
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')

                # Уменьшаем размер, сохраняя пропорции
                img.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)

                # Сохраняем с сжатием
                img.save(output_path, format="JPEG", quality=JPEG_QUALITY, optimize=True)

            original_size = len(image_data)
            optimized_size = output_path.stat().st_size
            compression_ratio = (1 - optimized_size / original_size) * 100

            logger.info(
                f"Optimized: {output_path.name} | "
                f"Original: {original_size / 1024:.1f}KB → "
                f"Optimized: {optimized_size / 1024:.1f}KB | "
                f"Saved: {compression_ratio:.1f}%"
            )
            return True

        except asyncio.TimeoutError:
            logger.error(f"Timeout downloading image from {url}")
            return False
        except Exception as e:
            logger.error(f"Error processing image from {url}: {e}", exc_info=True)
            return False

    async def preload_product_photos(self, products: List[Dict]) -> Dict[str, int]:
        """
        Предзагрузить фото для списка товаров

        Args:
            products: Список товаров из Google Sheets

        Returns:
            Статистика: {"total": N, "downloaded": M, "skipped": K, "failed": L}
        """
        stats = {"total": 0, "downloaded": 0, "skipped": 0, "failed": 0}

        logger.info(f"Starting preload for {len(products)} products...")

        # Собираем все задачи для параллельного скачивания
        tasks = []

        for product in products:
            product_id = product.get('product_id')
            if not product_id:
                continue

            # Список всех возможных фото товара
            photo_urls = {
                'collage': product.get('collage_url'),
                '1': product.get('photo_1_url'),
                '2': product.get('photo_2_url'),
                '3': product.get('photo_3_url'),
                '4': product.get('photo_4_url'),
                '5': product.get('photo_5_url'),
                '6': product.get('photo_6_url'),
            }

            for photo_type, url in photo_urls.items():
                if not url:
                    continue

                stats["total"] += 1
                output_path = self._get_photo_path(product_id, photo_type)

                # Проверяем, существует ли уже файл
                if output_path.exists():
                    logger.debug(f"Skipping existing: {output_path.name}")
                    stats["skipped"] += 1
                    # Добавляем в маппинг
                    self.photo_map[(product_id, photo_type)] = output_path
                    continue

                # Добавляем задачу на скачивание
                tasks.append(self._process_photo(product_id, photo_type, url, output_path, stats))

        # Выполняем все задачи параллельно (но с ограничением)
        if tasks:
            logger.info(f"Downloading {len(tasks)} new photos (max 10 concurrent)...")
            # Ограничиваем количество одновременных загрузок
            semaphore = asyncio.Semaphore(10)

            async def limited_task(task):
                async with semaphore:
                    return await task

            await asyncio.gather(*[limited_task(task) for task in tasks])

        logger.info(
            f"Preload complete! Total: {stats['total']}, "
            f"Downloaded: {stats['downloaded']}, "
            f"Skipped: {stats['skipped']}, "
            f"Failed: {stats['failed']}"
        )

        return stats

    async def _process_photo(
        self,
        product_id: str,
        photo_type: str,
        url: str,
        output_path: Path,
        stats: Dict[str, int]
    ):
        """Обработать одно фото (для параллельного выполнения)"""
        success = await self._download_and_optimize(url, output_path)

        if success:
            stats["downloaded"] += 1
            self.photo_map[(product_id, photo_type)] = output_path
        else:
            stats["failed"] += 1

    def get_photo_path(self, product_id: str, photo_type: str) -> Optional[Path]:
        """
        Получить путь к оптимизированному фото товара

        Args:
            product_id: ID товара
            photo_type: Тип фото (collage, 1, 2, 3, 4, 5, 6)

        Returns:
            Path к файлу или None если файл не найден
        """
        # Сначала проверяем маппинг
        if (product_id, photo_type) in self.photo_map:
            path = self.photo_map[(product_id, photo_type)]
            if path.exists():
                return path

        # Если нет в маппинге, проверяем напрямую на диске
        path = self._get_photo_path(product_id, photo_type)
        if path.exists():
            self.photo_map[(product_id, photo_type)] = path
            return path

        return None

    def cleanup_orphaned_photos(self, active_product_ids: List[str]):
        """
        Удалить фото товаров, которых больше нет в каталоге

        Args:
            active_product_ids: Список ID активных товаров
        """
        logger.info("Cleaning up orphaned product photos...")
        deleted_count = 0

        active_ids_set = set(active_product_ids)

        for file_path in self.photos_dir.glob("*.jpg"):
            # Извлекаем product_id из имени файла
            # Формат: {product_id}_{photo_type}.jpg
            parts = file_path.stem.split('_', 1)
            if len(parts) < 2:
                continue

            product_id = parts[0]

            if product_id not in active_ids_set:
                logger.info(f"Deleting orphaned photo: {file_path.name}")
                file_path.unlink()
                deleted_count += 1

                # Удаляем из маппинга
                keys_to_remove = [k for k in self.photo_map.keys() if k[0] == product_id]
                for key in keys_to_remove:
                    del self.photo_map[key]

        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} orphaned photos")
        else:
            logger.info("No orphaned photos found")

    def get_stats(self) -> Dict[str, int]:
        """Получить статистику хранилища"""
        total_files = len(list(self.photos_dir.glob("*.jpg")))
        total_size = sum(f.stat().st_size for f in self.photos_dir.glob("*.jpg"))

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / 1024 / 1024, 2),
            "cached_mappings": len(self.photo_map)
        }


# Singleton instance
photo_preloader = PhotoPreloader()
