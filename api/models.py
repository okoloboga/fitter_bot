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


class UserMeasurement(Base):
    """Модель параметров тела пользователя"""
    __tablename__ = "user_measurements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.tg_id", ondelete="CASCADE"), unique=True, nullable=False)
    height = Column(Integer, nullable=False)  # Рост в см
    chest = Column(Integer, nullable=False)   # Обхват груди в см
    waist = Column(Integer, nullable=False)   # Обхват талии в см
    hips = Column(Integer, nullable=False)    # Обхват бедер в см
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
