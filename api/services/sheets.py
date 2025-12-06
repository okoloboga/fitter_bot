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
        'Фото 5': 'photo_5_url',
        'Фото 6': 'photo_6_url',
        'Коллаж': 'collage_url',
        'Активен': 'is_active',
        'Таблица размеров': 'size_table_id'
    }
    
    SIZE_TABLES_MAPPING = {
        'Категория': 'table_id',
        'Размер': 'size',
        'Российский размер': 'russian_size',
        'Длина плеч': 'shoulder_length',
        'Длина плеч мин': 'shoulder_length_min',
        'Длина плеч макс': 'shoulder_length_max',
        'Ширина спины': 'back_width',
        'Ширина спины мин': 'back_width_min',
        'Ширина спины макс': 'back_width_max',
        'Длина рукава': 'sleeve_length',
        'Длина рукава мин': 'sleeve_length_min',
        'Длина рукава макс': 'sleeve_length_max',
        'Длина изделия по спинке': 'back_length',
        'Длина изделия по спинке мин': 'back_length_min',
        'Длина изделия по спинке макс': 'back_length_max',
        'Обхват груди': 'chest',
        'Обхват груди мин': 'chest_min',
        'Обхват груди макс': 'chest_max',
        'Обхват талии': 'waist',
        'Обхват талии мин': 'waist_min',
        'Обхват талии макс': 'waist_max',
        'Обхват бедер': 'hips',
        'Обхват бедер мин': 'hips_min',
        'Обхват бедер макс': 'hips_max',
        'Длина брюк': 'pants_length',
        'Длина брюк мин': 'pants_length_min',
        'Длина брюк макс': 'pants_length_max',
        'Обхват в поясе': 'waist_girth',
        'Обхват в поясе мин': 'waist_girth_min',
        'Обхват в поясе макс': 'waist_girth_max',
        'Высота посадки': 'rise_height',
        'Высота посадки мин': 'rise_height_min',
        'Высота посадки макс': 'rise_height_max',
        'Высота посадки сзади': 'back_rise_height',
        'Высота посадки сзади мин': 'back_rise_height_min',
        'Высота посадки сзади макс': 'back_rise_height_max'
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
        # Очищаем ключи от лишних пробелов, которые могут появиться в Google Sheets
        cleaned_row = {k.strip(): v for k, v in row.items()}
        
        result = {}
        for rus_name, eng_key in mapping.items():
            # Пробуем получить значение по русскому названию
            if rus_name in cleaned_row:
                result[eng_key] = cleaned_row[rus_name]
            # Если не нашли, пробуем по английскому ключу (для обратной совместимости)
            elif eng_key in cleaned_row:
                result[eng_key] = cleaned_row[eng_key]
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
                        'photo_5_url': convert_google_drive_url(mapped_row['photo_5_url']),
                        'photo_6_url': convert_google_drive_url(mapped_row['photo_6_url']),
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
                        'photo_5_url': convert_google_drive_url(mapped_row['photo_5_url']),
                        'photo_6_url': convert_google_drive_url(mapped_row['photo_6_url']),
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
            logger.info(f"Read {len(records)} records from 'Размеры' sheet: {records}")

            size_table = []
            for row in records:
                # Преобразуем русские названия в английские ключи
                mapped_row = self._map_row(row, self.SIZE_TABLES_MAPPING)

                if mapped_row['table_id'] == table_id:
                    size_entry = {
                        'table_id': mapped_row['table_id'],
                        'size': mapped_row['size'],
                        'russian_size': mapped_row.get('russian_size'),
                    }

                    # Добавляем все числовые параметры (min/max)
                    numeric_params = [
                        'shoulder_length', 'back_width', 'sleeve_length', 'back_length',
                        'chest', 'waist', 'hips', 'pants_length',
                        'waist_girth', 'rise_height', 'back_rise_height'
                    ]

                    for param in numeric_params:
                        min_key = f'{param}_min'
                        max_key = f'{param}_max'

                        min_val = mapped_row.get(min_key)
                        max_val = mapped_row.get(max_key)

                        # Fallback to single value if min/max are not present
                        if min_val is None and max_val is None:
                            # The key for a single value in the mapping is the English key itself
                            # We need to find the Russian name from the mapping to look up in the row
                            # This is complex, so let's assume a simpler direct lookup for now
                            # A better approach would be to reverse the mapping.
                            # For now, we will try to get the direct english key, which might be present
                            single_val = mapped_row.get(param)
                            if single_val is not None:
                                min_val = single_val
                                max_val = single_val

                        size_entry[min_key] = int(min_val) if min_val not in [None, ''] else None
                        size_entry[max_key] = int(max_val) if max_val not in [None, ''] else None

                    logger.info(f"Constructed size_entry for size {size_entry.get('size')}: {size_entry}")
                    size_table.append(size_entry)

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
