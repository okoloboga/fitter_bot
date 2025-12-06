"""
API endpoints для работы с параметрами пользователей
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.sql import func

from api.database import get_db
from api.models import UserMeasurement, User
from api.schemas import MeasurementsCreate, MeasurementsResponse

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.post("/{user_tg_id}", response_model=MeasurementsResponse)
async def create_or_update_measurements(
    user_tg_id: int,
    measurements: MeasurementsCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать или обновить параметры пользователя по tg_id (частичное обновление)"""
    # Проверяем существование пользователя
    result = await db.execute(select(User).where(User.tg_id == user_tg_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User with this tg_id not found")

    # Проверяем, существуют ли уже параметры
    result = await db.execute(
        select(UserMeasurement).where(UserMeasurement.user_id == user_tg_id)
    )
    existing = result.scalar_one_or_none()

    # Получаем только переданные поля (не None)
    update_data = measurements.model_dump(exclude_unset=True)

    if existing:
        # Обновляем только переданные поля
        for field, value in update_data.items():
            setattr(existing, field, value)
        existing.updated_at = func.now()

        await db.commit()
        await db.refresh(existing)
        return existing
    else:
        # Создаем новую запись с переданными полями
        new_measurements = UserMeasurement(
            user_id=user_tg_id,
            **update_data
        )

        db.add(new_measurements)
        await db.commit()
        await db.refresh(new_measurements)
        return new_measurements


@router.get("/{user_tg_id}", response_model=MeasurementsResponse)
async def get_measurements(user_tg_id: int, db: AsyncSession = Depends(get_db)):
    """Получить параметры пользователя по tg_id"""
    result = await db.execute(
        select(UserMeasurement).where(UserMeasurement.user_id == user_tg_id)
    )
    measurements = result.scalar_one_or_none()

    if not measurements:
        raise HTTPException(status_code=404, detail="Measurements not found")

    return measurements
