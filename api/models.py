"""
SQLAlchemy модели для БД
"""
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from api.database import Base


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    tg_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    last_activity = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), index=True)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Relationships
    measurements = relationship("UserMeasurement", back_populates="user", uselist=False, cascade="all, delete-orphan")
    favorites = relationship("Favorite", back_populates="user", cascade="all, delete-orphan")
    photos = relationship("UserPhoto", back_populates="user", cascade="all, delete-orphan")
    try_on_history = relationship("TryOnHistory", back_populates="user", cascade="all, delete-orphan")


class UserMeasurement(Base):
    """Модель параметров тела пользователя"""
    __tablename__ = "user_measurements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="CASCADE"), unique=True, nullable=False)

    # Все параметры опциональны - пользователь может заполнять выборочно
    russian_size = Column(String(20), nullable=True)  # Российский размер (например "42-44")
    shoulder_length = Column(Integer, nullable=True)  # Длина плеч в см
    back_width = Column(Integer, nullable=True)       # Ширина спины в см
    sleeve_length = Column(Integer, nullable=True)    # Длина рукава в см
    back_length = Column(Integer, nullable=True)      # Длина изделия по спинке в см
    chest = Column(Integer, nullable=True)            # Обхват груди в см
    waist = Column(Integer, nullable=True)            # Обхват талии в см
    hips = Column(Integer, nullable=True)             # Обхват бедер в см
    pants_length = Column(Integer, nullable=True)     # Длина брюк в см
    waist_girth = Column(Integer, nullable=True)      # Обхват в поясе в см
    rise_height = Column(Integer, nullable=True)      # Высота посадки в см
    back_rise_height = Column(Integer, nullable=True) # Высота посадки сзади в см

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="measurements")


class Favorite(Base):
    """Модель избранных товаров"""
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(100), nullable=False)  # ID товара из Google Sheets
    added_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user = relationship("User", back_populates="favorites")

    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='unique_user_product'),
    )


class UserPhoto(Base):
    """Модель фотографий пользователей для примерки"""
    __tablename__ = "user_photos"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="CASCADE"), nullable=False, index=True)
    file_id = Column(String(255), nullable=False)  # Telegram file_id
    file_path = Column(String(500), nullable=False)  # Путь к файлу на сервере
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_active = Column(Boolean, default=True, nullable=False)  # Активно ли фото
    consent_given = Column(Boolean, default=False, nullable=False)  # Согласие на обработку

    # Relationships
    user = relationship("User", back_populates="photos")
    try_on_history = relationship("TryOnHistory", back_populates="user_photo", cascade="all, delete-orphan")


class TryOnHistory(Base):
    """Модель истории примерок"""
    __tablename__ = "try_on_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(String(100), nullable=False, index=True)  # ID товара из Google Sheets
    user_photo_id = Column(Integer, ForeignKey("user_photos.id", ondelete="CASCADE"), nullable=False)
    result_file_path = Column(String(500), nullable=True)  # Путь к результату примерки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    generation_time = Column(Integer, nullable=True)  # Время генерации в секундах
    status = Column(String(20), nullable=False, default="processing")  # processing, success, failed

    # Relationships
    user = relationship("User", back_populates="try_on_history")
    user_photo = relationship("UserPhoto", back_populates="try_on_history")
