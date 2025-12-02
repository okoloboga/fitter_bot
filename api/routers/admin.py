"""
API endpoints для административной панели
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta

from api.database import get_db
from api.models import User, UserMeasurement, Favorite

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Получить статистику бота"""
    # Общее количество пользователей
    total_users_result = await db.execute(select(func.count()).select_from(User))
    total_users = total_users_result.scalar()

    # Новые пользователи за сегодня
    today = datetime.now().date()
    today_users_result = await db.execute(
        select(func.count()).select_from(User).where(func.date(User.created_at) == today)
    )
    today_users = today_users_result.scalar()

    # Новые за 7 дней
    week_ago = datetime.now() - timedelta(days=7)
    week_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    )
    week_users = week_users_result.scalar()

    # Новые за 30 дней
    month_ago = datetime.now() - timedelta(days=30)
    month_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= month_ago)
    )
    month_users = month_users_result.scalar()

    # Активные за 7 дней
    active_users_result = await db.execute(
        select(func.count()).select_from(User).where(User.last_activity >= week_ago)
    )
    active_users = active_users_result.scalar()

    # Пользователи с параметрами
    measurements_count_result = await db.execute(
        select(func.count()).select_from(UserMeasurement)
    )
    measurements_count = measurements_count_result.scalar()

    # Процент пользователей с параметрами
    measurements_percent = (measurements_count / total_users * 100) if total_users > 0 else 0

    # Всего добавлений в избранное
    favorites_count_result = await db.execute(
        select(func.count()).select_from(Favorite)
    )
    favorites_count = favorites_count_result.scalar()

    # ТОП-5 избранных товаров
    top_favorites_result = await db.execute(
        select(Favorite.product_id, func.count(Favorite.id).label('count'))
        .group_by(Favorite.product_id)
        .order_by(func.count(Favorite.id).desc())
        .limit(5)
    )
    top_favorites = top_favorites_result.all()

    return {
        "users": {
            "total": total_users,
            "today": today_users,
            "week": week_users,
            "month": month_users,
            "active_week": active_users
        },
        "measurements": {
            "count": measurements_count,
            "percent": round(measurements_percent, 1)
        },
        "favorites": {
            "total": favorites_count,
            "top": [{"product_id": row[0], "count": row[1]} for row in top_favorites]
        }
    }
