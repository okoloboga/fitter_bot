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
    height: int = Field(ge=140, le=200)
    chest: int = Field(ge=70, le=130)
    waist: int = Field(ge=50, le=110)
    hips: int = Field(ge=70, le=140)


class MeasurementsResponse(BaseModel):
    id: int
    user_id: int
    height: int
    chest: int
    waist: int
    hips: int
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
    size_table_id: str


class Category(BaseModel):
    category_id: str
    category_name: str
    display_order: int
    emoji: str
