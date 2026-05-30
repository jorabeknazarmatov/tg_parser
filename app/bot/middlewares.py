"""
Настройка middleware для бота aiogram.
Внедряет зависимости (БД, сервисы) через workflow_data.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Dispatcher

from app.middlewares.admin import LoggingMiddleware

if TYPE_CHECKING:
    from app.core.account_manager import AccountManager
    from app.core.config import Settings
    from app.repositories.account_repo import AccountRepository
    from app.repositories.task_repo import TaskRepository
    from app.repositories.user_repo import UserRepository
    from app.services.parser_service import ParserService
    from app.services.sender_service import SenderService
    from app.services.stats_service import StatsService


def setup_middlewares(
    dp: Dispatcher,
    settings: "Settings",
    account_manager: "AccountManager",
    parser_service: "ParserService",
    sender_service: "SenderService",
    stats_service: "StatsService",
    task_repo: "TaskRepository",
    user_repo: "UserRepository",
) -> None:
    """
    Настраивает все middleware и внедряет зависимости.

    Зависимости добавляются в workflow_data диспетчера — они доступны
    во всех обработчиках через аргументы функций.
    """
    # Регистрируем middleware для логирования
    dp.message.middleware(LoggingMiddleware())

    # Внедряем зависимости через workflow_data (глобальный DI контейнер)
    dp.workflow_data.update({
        "settings": settings,
        "account_manager": account_manager,
        "parser_service": parser_service,
        "sender_service": sender_service,
        "stats_service": stats_service,
        "task_repo": task_repo,
        "user_repo": user_repo,
    })
