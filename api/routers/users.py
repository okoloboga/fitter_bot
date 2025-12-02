"""
API endpoints для работы с пользователями
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.sql import func

from api.database import get_db
from api.models import User
from api.schemas import UserCreate, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверяем, существует ли пользователь
    result = await db.execute(select(User).where(User.tg_id == user_data.tg_id))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Обновляем last_activity
        await db.execute(
            update(User)
            .where(User.tg_id == user_data.tg_id)
            .values(last_activity=func.now())
        )
        await db.commit()
        await db.refresh(existing_user)
        return existing_user

    # Создаем нового пользователя
    new_user = User(
        tg_id=user_data.tg_id,
        username=user_data.username,
        first_name=user_data.first_name
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """Получить данные пользователя по ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.get("/by-tg-id/{tg_id}", response_model=UserResponse)
async def get_user_by_tg_id(tg_id: int, db: AsyncSession = Depends(get_db)):
    """Получить данные пользователя по Telegram ID"""
    result = await db.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put("/{user_id}/activity")
async def update_activity(user_id: int, db: AsyncSession = Depends(get_db)):
    """Обновить время последней активности"""
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(last_activity=func.now())
    )
    await db.commit()

    return {"status": "ok", "message": "Activity updated"}
