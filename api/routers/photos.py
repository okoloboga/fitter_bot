"""
API endpoints для работы с фото пользователей и примерками
"""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_
from typing import List, Optional
from datetime import datetime, date
import os
import logging
import uuid

from pydantic import BaseModel

from api.database import get_db
from api.models import User, UserPhoto, TryOnHistory
from api.schemas import (
    UserPhotoCreate,
    UserPhotoResponse,
    UserPhotosResponse,
    TryOnHistoryCreate,
    TryOnHistoryResponse,
    TryOnHistoryListResponse
)
from api.services.sheets import sheets_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["photos"])


class TryOnStatsResponse(BaseModel):
    total: int
    today: int
    week: int
    month: int
    avg_generation_time: Optional[float]
    success_rate: float


# Определяем базовую директорию для хранения фото в контейнере
USER_PHOTOS_DIR = "/app/storage/user_photos"


# === Photo Management ===

@router.post("/photos/upload", response_model=dict)
async def upload_photo(
    db: AsyncSession = Depends(get_db),
    user_id: int = Form(...),
    file_id: str = Form(...),
    consent_given: bool = Form(...),
    file: UploadFile = File(...)
):
    """
    Загрузка файла фото и сохранение информации в БД
    """
    file_path = None
    try:
        # Проверяем пользователя
        result = await db.execute(select(User).where(User.tg_id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Создаем директорию пользователя, если ее нет
        user_dir = os.path.join(USER_PHOTOS_DIR, str(user_id))
        os.makedirs(user_dir, exist_ok=True)
        
        # Генерируем уникальное имя файла, чтобы избежать конфликтов
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(user_dir, unique_filename)
        
        # Сохраняем файл
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        # Проверяем лимит фото (максимум 3)
        result = await db.execute(
            select(func.count(UserPhoto.id)).where(UserPhoto.user_id == user_id)
        )
        photo_count = result.scalar() or 0

        if photo_count >= 3:
            # Удаляем самое старое фото
            result = await db.execute(
                select(UserPhoto)
                .where(UserPhoto.user_id == user_id)
                .order_by(UserPhoto.uploaded_at.asc())
                .limit(1)
            )
            oldest_photo = result.scalar_one_or_none()

            if oldest_photo:
                # Удаляем файл со диска
                if oldest_photo.file_path and os.path.exists(oldest_photo.file_path):
                    os.remove(oldest_photo.file_path)
                await db.delete(oldest_photo)

        # Создаем новое фото
        new_photo = UserPhoto(
            user_id=user_id,
            file_id=file_id,
            file_path=file_path,
            consent_given=consent_given,
            is_active=True
        )

        db.add(new_photo)
        await db.commit()
        await db.refresh(new_photo)

        return {
            "success": True,
            "photo": {
                "id": new_photo.id,
                "file_id": new_photo.file_id,
                "file_path": new_photo.file_path,
                "uploaded_at": new_photo.uploaded_at.isoformat()
            }
        }

    except HTTPException:
        await db.rollback()
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        await db.rollback()
        # Попытаемся удалить сохраненный файл, если что-то пошло не так
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Failed to upload photo: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error during file upload.")


@router.get("/photos/{tg_id}")
async def get_user_photos(tg_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение всех фото пользователя
    """
    try:
        result = await db.execute(
            select(UserPhoto)
            .where(UserPhoto.user_id == tg_id)
            .order_by(UserPhoto.uploaded_at.desc())
        )
        photos = result.scalars().all()

        return {
            "success": True,
            "photos": [
                {
                    "id": photo.id,
                    "file_id": photo.file_id,
                    "file_path": photo.file_path,
                    "uploaded_at": photo.uploaded_at.isoformat(),
                    "is_active": photo.is_active
                }
                for photo in photos
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get user photos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/photos/{photo_id}")
async def delete_photo(photo_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаление фото пользователя
    """
    try:
        result = await db.execute(select(UserPhoto).where(UserPhoto.id == photo_id))
        photo = result.scalar_one_or_none()

        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")

        # Удаляем файл
        if os.path.exists(photo.file_path):
            os.remove(photo.file_path)

        await db.delete(photo)
        await db.commit()

        return {"success": True, "message": "Photo deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete photo: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# === Try-On Management ===

@router.post("/tryon/create")
async def create_tryon(req: TryOnHistoryCreate, db: AsyncSession = Depends(get_db)):
    """
    Создание записи о примерке (статус processing)
    """
    try:
        # Проверяем rate limit (20 примерок в день)
        today = date.today()
        result = await db.execute(
            select(func.count(TryOnHistory.id))
            .where(
                and_(
                    TryOnHistory.user_id == req.user_id,
                    func.date(TryOnHistory.created_at) == today
                )
            )
        )
        today_count = result.scalar() or 0

        if today_count >= 20:
            return {
                "success": False,
                "error": "rate_limit",
                "message": "Ты достиг лимита примерок на сегодня (20/20). Попробуй завтра! 😊"
            }

        # Получаем данные о товаре из Google Sheets
        product = sheets_service.get_product_by_id(req.product_id)
        wb_link = product.get("wb_link") if product else None
        ozon_url = product.get("ozon_url") if product else None

        # Создаем запись
        tryon = TryOnHistory(
            user_id=req.user_id,
            product_id=req.product_id,
            user_photo_id=req.user_photo_id,
            status="processing",
            wb_link=wb_link,
            ozon_url=ozon_url
        )

        db.add(tryon)
        await db.commit()
        await db.refresh(tryon)

        return {
            "success": True,
            "tryon_id": tryon.id
        }

    except Exception as e:
        logger.error(f"Failed to create try-on: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TryOnUpdateRequest(BaseModel):
    status: str
    result_file_path: Optional[str] = None
    generation_time: Optional[int] = None


@router.put("/tryon/{tryon_id}")
async def update_tryon(
    tryon_id: int,
    req: TryOnUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление записи о примерке после генерации
    """
    try:
        result = await db.execute(select(TryOnHistory).where(TryOnHistory.id == tryon_id))
        tryon = result.scalar_one_or_none()

        if not tryon:
            raise HTTPException(status_code=404, detail="Try-on not found")

        tryon.status = req.status
        if req.result_file_path is not None:
            tryon.result_file_path = req.result_file_path
        if req.generation_time is not None:
            tryon.generation_time = req.generation_time

        await db.commit()

        logger.info(f"Updated try-on {tryon_id}: status={req.status}, path={req.result_file_path}")

        return {"success": True}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update try-on: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tryon/history/{tg_id}", response_model=TryOnHistoryListResponse)
async def get_tryon_history(tg_id: int, db: AsyncSession = Depends(get_db)):
    """
    Получение истории примерок пользователя
    """
    try:
        result = await db.execute(
            select(TryOnHistory)
            .where(
                and_(
                    TryOnHistory.user_id == tg_id,
                    TryOnHistory.status == "success"
                )
            )
            .order_by(TryOnHistory.created_at.desc())
        )
        history = result.scalars().all()

        return {
            "history": [
                {
                    "id": item.id,
                    "user_id": item.user_id,
                    "product_id": item.product_id,
                    "user_photo_id": item.user_photo_id,
                    "result_file_path": item.result_file_path,
                    "created_at": item.created_at,
                    "status": item.status,
                    "wb_link": item.wb_link,
                    "ozon_url": item.ozon_url,
                }
                for item in history
            ]
        }

    except Exception as e:
        logger.error(f"Failed to get try-on history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/tryon/{tryon_id}")
async def delete_tryon(tryon_id: int, db: AsyncSession = Depends(get_db)):
    """
    Удаление примерки из истории
    """
    try:
        result = await db.execute(select(TryOnHistory).where(TryOnHistory.id == tryon_id))
        tryon = result.scalar_one_or_none()

        if not tryon:
            raise HTTPException(status_code=404, detail="Try-on not found")

        # Удаляем файл результата
        if tryon.result_file_path and os.path.exists(tryon.result_file_path):
            os.remove(tryon.result_file_path)

        await db.delete(tryon)
        await db.commit()

        return {"success": True, "message": "Try-on deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete try-on: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tryon/check-limit/{tg_id}")
async def check_tryon_limit(tg_id: int, db: AsyncSession = Depends(get_db)):
    """
    Проверка лимита примерок на сегодня
    """
    try:
        today = date.today()
        result = await db.execute(
            select(func.count(TryOnHistory.id))
            .where(
                and_(
                    TryOnHistory.user_id == tg_id,
                    func.date(TryOnHistory.created_at) == today
                )
            )
        )
        today_count = result.scalar() or 0

        return {
            "success": True,
            "count": today_count,
            "limit": 20,
            "remaining": max(0, 20 - today_count),
            "limit_reached": today_count >= 20
        }

    except Exception as e:
        logger.error(f"Failed to check try-on limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))
