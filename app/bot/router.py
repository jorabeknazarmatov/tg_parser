"""
Регистрация всех обработчиков и фильтров бота.
"""
from __future__ import annotations

from aiogram import Dispatcher, Router

from app.handlers import accounts, find, send_test, start, stats, status, stop


def register_all_handlers(dp: Dispatcher) -> None:
    """
    Регистрирует все роутеры обработчиков в диспетчере.

    Args:
        dp: Диспетчер aiogram
    """
    # Создаём главный роутер
    main_router = Router()

    # Включаем все роутеры обработчиков
    main_router.include_router(start.router)
    main_router.include_router(find.router)
    main_router.include_router(status.router)
    main_router.include_router(stop.router)
    main_router.include_router(stats.router)
    main_router.include_router(accounts.router)
    main_router.include_router(send_test.router)

    # Регистрируем главный роутер в диспетчере
    dp.include_router(main_router)
