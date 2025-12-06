"""
Pydantic схемы для API
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


# User schemas
class UserCreate(BaseModel):
    tg_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    tg_id: int
    username: Optional[str]
    first_name: Optional[str]
    created_at: datetime
    last_activity: datetime
    is_admin: bool

    class Config:
        from_attributes = True


# Measurements schemas
class MeasurementsCreate(BaseModel):
    """Схема для создания/обновления параметров (все поля опциональны)"""
    russian_size: Optional[str] = Field(None)
    shoulder_length: Optional[int] = Field(None, ge=0)
    back_width: Optional[int] = Field(None, ge=0)
    sleeve_length: Optional[int] = Field(None, ge=0)
    back_length: Optional[int] = Field(None, ge=0)
    chest: Optional[int] = Field(None, ge=0)
    waist: Optional[int] = Field(None, ge=0)
    hips: Optional[int] = Field(None, ge=0)
    pants_length: Optional[int] = Field(None, ge=0)
    waist_girth: Optional[int] = Field(None, ge=0)
    rise_height: Optional[int] = Field(None, ge=0)
    back_rise_height: Optional[int] = Field(None, ge=0)


class MeasurementsResponse(BaseModel):
    """Схема для ответа с параметрами пользователя"""
    id: int
    user_id: int
    russian_size: Optional[str]
    shoulder_length: Optional[int]
    back_width: Optional[int]
    sleeve_length: Optional[int]
    back_length: Optional[int]
    chest: Optional[int]
    waist: Optional[int]
    hips: Optional[int]
    pants_length: Optional[int]
    waist_girth: Optional[int]
    rise_height: Optional[int]
    back_rise_height: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True


# Favorite schemas
class FavoriteCreate(BaseModel):
    user_id: int
    product_id: str


class FavoriteResponse(BaseModel):
    id: int
    user_id: int
    product_id: str
    added_at: datetime

    class Config:
        from_attributes = True


# Size recommendation schemas
class SizeRecommendRequest(BaseModel):
    user_id: int
    product_id: str


class SizeRecommendResponse(BaseModel):
    success: bool
    recommended_size: Optional[str] = None
    alternative_size: Optional[str] = None
    confidence: str
    message: str
    details: Optional[dict] = None


# Product schemas (from Google Sheets)
class Product(BaseModel):
    product_id: str
    category: str
    name: str
    description: str
    wb_link: str
    available_sizes: str
    collage_url: str
    photo_1_url: str
    photo_2_url: str
    photo_3_url: str
    photo_4_url: str
    photo_5_url: str
    photo_6_url: str
    size_table_id: str


class Category(BaseModel):
    category_id: str
    category_name: str
    display_order: int
    emoji: str
