"""
Конфигурация базы данных
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
import os

# URL подключения к БД
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/fitting_bot")

# Создание async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Логирование SQL запросов
    pool_size=20,
    max_overflow=10
)

# Создание async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class для моделей
Base = declarative_base()


async def get_db():
    """Dependency для получения сессии БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Инициализация БД (создание таблиц)"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
