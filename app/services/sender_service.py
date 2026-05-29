"""
Сервис рассылки — оркестрирует запуск и остановку задач рассылки.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.models.task import Task
    from app.repositories.task_repo import TaskRepository
    from app.repositories.user_repo import UserRepository
    from app.sender.engine import SenderEngine

logger = get_logger("sender")


class SenderService:
    """
    Сервис управления задачами рассылки.
    Обеспечивает запуск, остановку и мониторинг фоновых задач отправки.
    """

    def __init__(
        self,
        engine: "SenderEngine",
        task_repo: "TaskRepository",
        user_repo: "UserRepository",
    ) -> None:
        # Движок рассылки
        self._engine = engine
        # Репозиторий задач
        self._task_repo = task_repo
        # Репозиторий пользователей
        self._user_repo = user_repo
        # Текущая asyncio задача
        self._current_task: Optional[asyncio.Task] = None

    async def start_send_task(self) -> "Task":
        """
        Создаёт и запускает задачу рассылки в фоне.

        Returns:
            Созданная задача

        Raises:
            RuntimeError: Если уже есть активная задача
        """
        active = await self._task_repo.get_active()
        if active:
            raise RuntimeError(
                f"Уже выполняется задача #{active.id} ({active.type})"
            )

        # Проверяем наличие пользователей для отправки
        unsent = await self._user_repo.count_unsent()
        if unsent == 0:
            raise RuntimeError(
                "Нет пользователей для рассылки. Сначала запустите парсинг (/find)."
            )

        # Создаём задачу в БД
        task = await self._task_repo.create("send")

        # Запускаем рассылку как фоновую задачу
        self._current_task = asyncio.create_task(
            self._run_send(task.id),
            name=f"send_task_{task.id}",
        )

        logger.info("Задача рассылки создана", task_id=task.id, unsent=unsent)
        return task

    async def _run_send(self, task_id: int) -> None:
        """
        Внутренняя функция запуска рассылки.

        Args:
            task_id: ID задачи
        """
        try:
            await self._engine.send_all(task_id)
        except Exception as exc:
            logger.error(
                "Ошибка фоновой рассылки",
                task_id=task_id,
                error=str(exc),
            )
            await self._task_repo.update_status(task_id, "failed")

    async def stop_send_task(self) -> None:
        """Останавливает текущую задачу рассылки."""
        self._engine.stop()

        if self._current_task and not self._current_task.done():
            self._current_task.cancel()
            try:
                await asyncio.wait_for(asyncio.shield(self._current_task), timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        logger.info("Задача рассылки остановлена")
