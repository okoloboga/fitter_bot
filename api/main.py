"""
Главный файл FastAPI приложения
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from api.database import init_db
from api.routers import users, measurements, favorites, catalog, size_recommend, admin, photos

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
# Добавляем явную настройку для логгера сервиса
sheets_logger = logging.getLogger("api.services.sheets")
sheets_logger.setLevel(logging.INFO)
sheets_logger.propagate = True


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events"""
    logger.info("Starting FastAPI application...")

    # Инициализация БД
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield

    logger.info("Shutting down FastAPI application...")


# Создание приложения
app = FastAPI(
    title="Fitting Bot API",
    description="API для Telegram бота по подбору одежды",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
# Configure CORS origins from environment variable
CORS_ALLOWED_ORIGINS_ENV = os.getenv("CORS_ALLOWED_ORIGINS", "")
if CORS_ALLOWED_ORIGINS_ENV:
    CORS_ALLOWED_ORIGINS = [origin.strip() for origin in CORS_ALLOWED_ORIGINS_ENV.split(',')]
else:
    CORS_ALLOWED_ORIGINS = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(users.router, prefix="/api")
app.include_router(measurements.router, prefix="/api")
app.include_router(favorites.router, prefix="/api")
app.include_router(catalog.router, prefix="/api")
app.include_router(size_recommend.router, prefix="/api")
app.include_router(photos.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
async def root():
    """Корневой endpoint"""
    return {
        "message": "Fitting Bot API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
@app.head("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
