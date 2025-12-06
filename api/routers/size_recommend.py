"""
API endpoints для подбора размеров
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models import UserMeasurement
from api.schemas import SizeRecommendRequest, SizeRecommendResponse
from api.services.sheets import sheets_service
from api.services.size_matcher import size_matcher_service

router = APIRouter(prefix="/size", tags=["size"])
logger = logging.getLogger(__name__)


@router.post("/recommend", response_model=SizeRecommendResponse)
async def recommend_size(
    request: SizeRecommendRequest,
    db: AsyncSession = Depends(get_db)
):
    """Рекомендовать размер на основе параметров пользователя"""
    logger.info("--- Size Recommendation Router: Start ---")
    logger.info(f"Received request for user_id: {request.user_id}, product_id: {request.product_id}")

    # Получаем параметры пользователя
    result = await db.execute(
        select(UserMeasurement).where(UserMeasurement.user_id == request.user_id)
    )
    measurements = result.scalar_one_or_none()

    if not measurements:
        logger.warning("User has no measurements in the database.")
        return SizeRecommendResponse(
            success=False,
            recommended_size=None,
            alternative_size=None,
            confidence="none",
            message="📐 Укажи свои параметры, чтобы получить рекомендацию по размеру",
            details={"reason": "no_measurements"}
        )

    # Получаем информацию о товаре
    logger.info(f"Fetching product data for product_id: {request.product_id}")
    product = sheets_service.get_product_by_id(request.product_id)

    if not product:
        logger.error(f"Product with id {request.product_id} not found in Google Sheets.")
        raise HTTPException(status_code=404, detail="Product not found")
    
    logger.info(f"Product data found: {product}")

    # Получаем таблицу размеров по категории товара
    size_table_id = product.get('category')
    if not size_table_id:
        logger.error(f"Product {request.product_id} has no 'category' defined.")
        raise HTTPException(status_code=404, detail="Product category not found, cannot determine size table")

    logger.info(f"Using product category '{size_table_id}' as the key to find the size table.")
    size_table = sheets_service.get_size_table(size_table_id)

    if not size_table:
        logger.warning(f"Size table not found for category '{size_table_id}'. The 'get_size_table' service returned an empty list.")
        return SizeRecommendResponse(
            success=False,
            recommended_size=None,
            alternative_size=None,
            confidence="none",
            message="⚠️ Таблица размеров для данной категории не найдена",
            details={"reason": "no_size_table_for_category"}
        )
    
    logger.info(f"Found size table for '{size_table_id}' with {len(size_table)} rows.")

    # Парсим доступные размеры
    available_sizes_str = product.get('available_sizes', '')
    available_sizes = [s.strip() for s in available_sizes_str.split(',') if s.strip()]
    logger.info(f"Product available sizes: {available_sizes}")

    # Параметры пользователя в виде словаря
    user_measurements_dict = {
        param: getattr(measurements, param, None)
        for param in size_matcher_service.ALL_PARAMS
    }
    logger.info(f"Passing user measurements to matcher: {user_measurements_dict}")

    # Подбираем размер
    logger.info("Calling size_matcher_service.recommend_size...")
    recommendation = size_matcher_service.recommend_size(
        user_measurements=user_measurements_dict,
        size_table=size_table,
        available_sizes=available_sizes
    )
    logger.info(f"Received result from matcher service: {recommendation}")
    logger.info("--- Size Recommendation Router: End ---")

    return SizeRecommendResponse(**recommendation)
