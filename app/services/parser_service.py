"""
Сервис парсинга — оркестрирует запуск и остановку задач парсинга.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.core.account_manager import AccountManager
    from app.core.config import Settings
    from app.models.task import Task
    from app.parser.engine import ParserEngine
    from app.repositories.task_repo import TaskRepository
    from app.repositories.user_repo import UserRepository

logger = get_logger("parser")


class ParserService:
    """
    Сервис управления задачами парсинга.
    Обеспечивает запуск, остановку и мониторинг фоновых задач.
    """

    def __init__(
        self,
        engine: "ParserEngine",
        task_repo: "TaskRepository",
        user_repo: "UserRepository",
    ) -> None:
        # Движок парсинга
        self._engine = engine
        # Репозиторий задач
        self._task_repo = task_repo
        # Репозиторий пользователей
        self._user_repo = user_repo
        # Текущая asyncio задача
        self._current_task: Optional[asyncio.Task] = None

    async def start_parse_task(self) -> "Task":
        """
        Создаёт и запускает задачу парсинга в фоне.

        Returns:
            Созданная задача

        Raises:
            RuntimeError: Если уже есть активная задача
        """
        # Проверяем существующие задачи
        active = await self._task_repo.get_active()
        if active:
            raise RuntimeError(
                f"Уже выполняется задача #{active.id} ({active.type})"
            )

        # Создаём запись задачи в БД
        task = await self._task_repo.create("parse")

        # Запускаем парсинг как фоновую задачу asyncio
        self._current_task = asyncio.create_task(
            self._run_parse(task.id),
            name=f"parse_task_{task.id}",
        )

        logger.info("Задача парсинга создана", task_id=task.id)
        return task

    async def _run_parse(self, task_id: int) -> None:
        """
        Внутренняя функция запуска парсинга.
        Обрабатывает исключения и обновляет статус задачи.

        Args:
            task_id: ID задачи
        """
        try:
            await self._engine.parse_all(task_id)
        except Exception as exc:
            logger.error(
                "Ошибка фонового парсинга",
                task_id=task_id,
                error=str(exc),
            )
            await self._task_repo.update_status(task_id, "failed")

    async def stop_parse_task(self) -> None:
        """Останавливает текущую задачу парсинга."""
        self._engine.stop()

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._current_task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        logger.info("Задача парсинга остановлена")
