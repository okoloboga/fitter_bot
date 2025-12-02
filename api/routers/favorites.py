"""
API endpoints для работы с избранным
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List

from api.database import get_db
from api.models import Favorite, User
from api.schemas import FavoriteCreate, FavoriteResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/", response_model=FavoriteResponse)
async def add_to_favorites(favorite: FavoriteCreate, db: AsyncSession = Depends(get_db)):
    """Добавить товар в избранное. user_id здесь - это tg_id."""
    # Проверяем существование пользователя по tg_id
    result = await db.execute(select(User).where(User.tg_id == favorite.user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User with this tg_id not found")

    # Проверяем, есть ли уже в избранном
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == favorite.user_id,
            Favorite.product_id == favorite.product_id
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Создаем новую запись
    new_favorite = Favorite(
        user_id=favorite.user_id,
        product_id=favorite.product_id
    )

    db.add(new_favorite)
    await db.commit()
    await db.refresh(new_favorite)

    return new_favorite


@router.delete("/{user_tg_id}/{product_id}")
async def remove_from_favorites(
    user_tg_id: int,
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Удалить товар из избранного по tg_id"""
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user_tg_id,
            Favorite.product_id == product_id
        )
    )
    await db.commit()

    return {"status": "ok", "message": "Removed from favorites"}


@router.get("/{user_tg_id}", response_model=List[FavoriteResponse])
async def get_favorites(user_tg_id: int, db: AsyncSession = Depends(get_db)):
    """Получить список избранного пользователя по tg_id"""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == user_tg_id)
        .order_by(Favorite.added_at.desc())
    )
    favorites = result.scalars().all()

    return favorites


@router.get("/{user_tg_id}/check/{product_id}")
async def check_favorite(
    user_tg_id: int,
    product_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Проверить, находится ли товар в избранном по tg_id"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == user_tg_id,
            Favorite.product_id == product_id
        )
    )
    favorite = result.scalar_one_or_none()

    return {"is_favorite": favorite is not None}
