"""
API endpoints для подбора размеров
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.database import get_db
from api.models import UserMeasurement
from api.schemas import SizeRecommendRequest, SizeRecommendResponse
from api.services.sheets import sheets_service
from api.services.size_matcher import size_matcher_service

router = APIRouter(prefix="/size", tags=["size"])


@router.post("/recommend", response_model=SizeRecommendResponse)
async def recommend_size(
    request: SizeRecommendRequest,
    db: AsyncSession = Depends(get_db)
):
    """Рекомендовать размер на основе параметров пользователя"""
    # Получаем параметры пользователя
    result = await db.execute(
        select(UserMeasurement).where(UserMeasurement.user_id == request.user_id)
    )
    measurements = result.scalar_one_or_none()

    if not measurements:
        return SizeRecommendResponse(
            success=False,
            recommended_size=None,
            alternative_size=None,
            confidence="none",
            message="📐 Укажи свои параметры, чтобы получить рекомендацию по размеру",
            details={"reason": "no_measurements"}
        )

    # Получаем информацию о товаре
    product = sheets_service.get_product_by_id(request.product_id)

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Получаем таблицу размеров
    size_table_id = product.get('size_table_id', 'outerwear_standard')
    size_table = sheets_service.get_size_table(size_table_id)

    if not size_table:
        return SizeRecommendResponse(
            success=False,
            recommended_size=None,
            alternative_size=None,
            confidence="none",
            message="⚠️ Таблица размеров не найдена",
            details={"reason": "no_size_table"}
        )

    # Парсим доступные размеры
    available_sizes = [s.strip() for s in product['available_sizes'].split(',')]

    # Параметры пользователя в виде словаря
    user_measurements_dict = {
        'height': measurements.height,
        'chest': measurements.chest,
        'waist': measurements.waist,
        'hips': measurements.hips
    }

    # Подбираем размер
    recommendation = size_matcher_service.recommend_size(
        user_measurements=user_measurements_dict,
        size_table=size_table,
        available_sizes=available_sizes
    )

    return SizeRecommendResponse(**recommendation)
