"""
Модуль обработчиков бота
"""
from aiogram import Router

from . import start, catalog, favorites, measurements, admin, tryon

def register_handlers():
    """Регистрация всех обработчиков"""
    router = Router()

    # Порядок важен! Более специфичные обработчики должны быть выше
    router.include_router(tryon.router)
    router.include_router(measurements.router)
    router.include_router(catalog.router)
    router.include_router(favorites.router)
    router.include_router(admin.router)

    # Роутер с хендлерами "по умолчанию" (start, unknown) должен быть последним
    router.include_router(start.router)

    return router
