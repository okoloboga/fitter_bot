"""
Сервис для работы с Google Sheets
"""
import gspread
from google.oauth2.service_account import Credentials
from cachetools import TTLCache
import os
import logging
import re
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


def convert_google_drive_url(url: str) -> str:
    """
    Конвертирует Google Drive ссылку из формата для просмотра в формат прямой ссылки.

    Из: https://drive.google.com/file/d/{FILE_ID}/view?usp=sharing
    В: https://drive.google.com/uc?export=view&id={FILE_ID}

    Args:
        url: Исходная ссылка Google Drive

    Returns:
        Преобразованная ссылка или пустая строка, если URL пустой
    """
    # Проверяем на None, пустую строку или строку только с пробелами
    if not url or not isinstance(url, str) or not url.strip():
        logger.warning(f"Empty or invalid URL received: {repr(url)}")
        return ""

    url = url.strip()

    # Паттерн для извлечения ID файла из ссылки Google Drive
    pattern = r'drive\.google\.com/file/d/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, url)

    if match:
        file_id = match.group(1)
        converted_url = f"https://drive.google.com/uc?export=view&id={file_id}"
        logger.debug(f"Converted Google Drive URL: {url} -> {converted_url}")
        return converted_url

    # Если ссылка уже в правильном формате или не является Google Drive ссылкой
    logger.debug(f"URL passed through without conversion: {url}")
    return url

# Кеш для данных из Google Sheets
categories_cache = TTLCache(maxsize=1, ttl=600)  # 10 минут
products_cache = TTLCache(maxsize=100, ttl=300)  # 5 минут
size_tables_cache = TTLCache(maxsize=50, ttl=1800)  # 30 минут


class GoogleSheetsService:
    """Сервис для работы с Google Sheets"""
    
    # Маппинг русских названий столбцов на английские ключи
    CATEGORIES_MAPPING = {
        'ID': 'category_id',
        'Название': 'category_name',
        'Порядок': 'display_order',
        'Эмодзи': 'emoji'
    }
    
    PRODUCTS_MAPPING = {
        'ID товара': 'product_id',
        'Категория': 'category',
        'Название': 'name',
        'Описание': 'description',
        'Размеры': 'available_sizes',
        'Фото 1': 'photo_1_url',
        'Фото 2': 'photo_2_url',
        'Фото 3': 'photo_3_url',
        'Фото 4': 'photo_4_url',
        'Коллаж': 'collage_url',
        'Активен': 'is_active',
        'Таблица размеров': 'size_table_id'
    }
    
    SIZE_TABLES_MAPPING = {
        'ID таблицы': 'table_id',
        'Размер': 'size',
        'Рост мин': 'height_min',
        'Рост макс': 'height_max',
        'Грудь мин': 'chest_min',
        'Грудь макс': 'chest_max',
        'Талия мин': 'waist_min',
        'Талия макс': 'waist_max',
        'Бедра мин': 'hips_min',
        'Бедра макс': 'hips_max'
    }

    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._initialize()

    def _initialize(self):
        """Инициализация подключения к Google Sheets"""
        logger.info("Attempting to initialize Google Sheets...")
        try:
            creds_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH", "config/credentials.json")
            spreadsheet_id = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID")
            logger.info(f"Credentials path: {creds_path}")
            logger.info(f"Spreadsheet ID: {spreadsheet_id}")

            logger.info("Checking if credentials file exists...")
            if not os.path.exists(creds_path):
                logger.warning(f"Google Sheets credentials not found at {creds_path}")
                return

            if not spreadsheet_id:
                logger.warning("GOOGLE_SHEETS_SPREADSHEET_ID not set")
                return
            
            logger.info("Credentials file found and spreadsheet ID is set. Authenticating...")
            # Аутентификация
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets.readonly',
                'https://www.googleapis.com/auth/drive.readonly'
            ]

            credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
            self.client = gspread.authorize(credentials)
            
            logger.info("Authentication successful. Opening spreadsheet...")
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)

            logger.info("Google Sheets initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets: {e}", exc_info=True)
            self.client = None
            self.spreadsheet = None
    
    def _map_row(self, row: Dict, mapping: Dict) -> Dict:
        """
        Преобразует строку с русскими названиями столбцов в словарь с английскими ключами
        
        Args:
            row: Строка из Google Sheets (словарь)
            mapping: Маппинг русских названий на английские ключи
        
        Returns:
            Словарь с английскими ключами
        """
        result = {}
        for rus_name, eng_key in mapping.items():
            # Пробуем получить значение по русскому названию
            if rus_name in row:
                result[eng_key] = row[rus_name]
            # Если не нашли, пробуем по английскому ключу (для обратной совместимости)
            elif eng_key in row:
                result[eng_key] = row[eng_key]
            else:
                result[eng_key] = None
        
        return result

    def get_categories(self) -> List[Dict]:
        """Получить список категорий"""
        if 'categories' in categories_cache:
            return categories_cache['categories']

        if not self.spreadsheet:
            logger.error("Google Sheets not initialized. Cannot fetch categories.")
            return []

        try:
            worksheet = self.spreadsheet.worksheet("Категории")
            records = worksheet.get_all_records()

            categories = []
            for row in records:
                mapped_row = self._map_row(row, self.CATEGORIES_MAPPING)
                
                categories.append({
                    'category_id': str(mapped_row['category_id']),
                    'category_name': mapped_row['category_name'],
                    'display_order': int(mapped_row['display_order']) if mapped_row['display_order'] else 0,
                    'emoji': mapped_row['emoji']
                })

            categories = sorted(categories, key=lambda x: x['display_order'])
            categories_cache['categories'] = categories
            return categories

        except Exception as e:
            logger.error(f"Error fetching categories from Google Sheets: {e}", exc_info=True)
            return []

    def get_products_by_category(self, category_id: str) -> List[Dict]:
        """Получить товары по категории"""
        cache_key = f"products_{category_id}"
        if cache_key in products_cache:
            return products_cache[cache_key]

        if not self.spreadsheet:
            logger.error("Google Sheets not initialized. Cannot fetch products.")
            return []

        try:
            worksheet = self.spreadsheet.worksheet("Товары")
            records = worksheet.get_all_records()

            products = []
            for row in records:
                mapped_row = self._map_row(row, self.PRODUCTS_MAPPING)
                
                is_active = str(mapped_row.get('is_active', 'ДА')).upper() in ['ДА', 'TRUE', 'YES', '1']
                
                if str(mapped_row['category']) == category_id and is_active:
                    product_id = str(mapped_row['product_id'])
                    products.append({
                        'product_id': product_id,
                        'category': str(mapped_row['category']),
                        'name': mapped_row['name'],
                        'description': mapped_row['description'],
                        'wb_link': f"https://www.wildberries.ru/catalog/{product_id}/detail.aspx",
                        'available_sizes': mapped_row['available_sizes'],
                        'collage_url': convert_google_drive_url(mapped_row['collage_url']),
                        'photo_1_url': convert_google_drive_url(mapped_row['photo_1_url']),
                        'photo_2_url': convert_google_drive_url(mapped_row['photo_2_url']),
                        'photo_3_url': convert_google_drive_url(mapped_row['photo_3_url']),
                        'photo_4_url': convert_google_drive_url(mapped_row['photo_4_url']),
                        'size_table_id': str(mapped_row.get('size_table_id') or 'outerwear_standard'),
                        'is_active': is_active
                    })

            products_cache[cache_key] = products
            return products

        except Exception as e:
            logger.error(f"Error fetching products from Google Sheets: {e}", exc_info=True)
            return []

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        """Получить товар по ID"""
        cache_key = f"product_{product_id}"
        if cache_key in products_cache:
            return products_cache[cache_key]

        if not self.spreadsheet:
            logger.error("Google Sheets not initialized. Cannot fetch product.")
            return None

        try:
            worksheet = self.spreadsheet.worksheet("Товары")
            records = worksheet.get_all_records()

            for row in records:
                mapped_row = self._map_row(row, self.PRODUCTS_MAPPING)
                
                if str(mapped_row['product_id']) == product_id:
                    is_active = str(mapped_row.get('is_active', 'ДА')).upper() in ['ДА', 'TRUE', 'YES', '1']
                    prod_id = str(mapped_row['product_id'])

                    product = {
                        'product_id': prod_id,
                        'category': str(mapped_row['category']),
                        'name': mapped_row['name'],
                        'description': mapped_row['description'],
                        'wb_link': f"https://www.wildberries.ru/catalog/{prod_id}/detail.aspx",
                        'available_sizes': mapped_row['available_sizes'],
                        'collage_url': convert_google_drive_url(mapped_row['collage_url']),
                        'photo_1_url': convert_google_drive_url(mapped_row['photo_1_url']),
                        'photo_2_url': convert_google_drive_url(mapped_row['photo_2_url']),
                        'photo_3_url': convert_google_drive_url(mapped_row['photo_3_url']),
                        'photo_4_url': convert_google_drive_url(mapped_row['photo_4_url']),
                        'size_table_id': str(mapped_row.get('size_table_id') or 'outerwear_standard'),
                        'is_active': is_active
                    }
                    products_cache[cache_key] = product
                    return product

            return None

        except Exception as e:
            logger.error(f"Error fetching product from Google Sheets: {e}", exc_info=True)
            return None

    def get_size_table(self, table_id: str) -> List[Dict]:
        """Получить таблицу размеров"""
        cache_key = f"size_table_{table_id}"

        # Проверка кеша
        if cache_key in size_tables_cache:
            return size_tables_cache[cache_key]

        if not self.spreadsheet:
            logger.warning("Google Sheets not initialized, returning empty size table")
            return []

        try:
            worksheet = self.spreadsheet.worksheet("Размеры")
            records = worksheet.get_all_records()

            size_table = []
            for row in records:
                # Преобразуем русские названия в английские ключи
                mapped_row = self._map_row(row, self.SIZE_TABLES_MAPPING)
                
                if mapped_row['table_id'] == table_id:
                    size_table.append({
                        'table_id': mapped_row['table_id'],
                        'size': mapped_row['size'],
                        'height_min': int(mapped_row['height_min']) if mapped_row.get('height_min') else None,
                        'height_max': int(mapped_row['height_max']) if mapped_row.get('height_max') else None,
                        'chest_min': int(mapped_row['chest_min']) if mapped_row.get('chest_min') else None,
                        'chest_max': int(mapped_row['chest_max']) if mapped_row.get('chest_max') else None,
                        'waist_min': int(mapped_row['waist_min']) if mapped_row.get('waist_min') else None,
                        'waist_max': int(mapped_row['waist_max']) if mapped_row.get('waist_max') else None,
                        'hips_min': int(mapped_row['hips_min']) if mapped_row.get('hips_min') else None,
                        'hips_max': int(mapped_row['hips_max']) if mapped_row.get('hips_max') else None,
                    })

            # Сохранение в кеш
            size_tables_cache[cache_key] = size_table

            return size_table

        except Exception as e:
            logger.error(f"Error fetching size table from Google Sheets: {e}")
            return []

    def clear_cache(self):
        """Очистить кеш"""
        categories_cache.clear()
        products_cache.clear()
        size_tables_cache.clear()
        logger.info("Google Sheets cache cleared")


# Singleton instance
sheets_service = GoogleSheetsService()
