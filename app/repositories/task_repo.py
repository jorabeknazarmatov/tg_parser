"""
Репозиторий для управления задачами фонового выполнения.
"""
from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepository:
    """Репозиторий для создания и обновления задач."""

    def __init__(self, session: AsyncSession) -> None:
        # Сессия базы данных
        self._session = session

    async def get_active(self) -> Task | None:
        """
        Возвращает активную задачу (статус running или pending).
        Используется для проверки занятости системы.
        """
        result = await self._session.execute(
            select(Task)
            .where(Task.status.in_(["running", "pending"]))
            .order_by(Task.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(self, task_type: str) -> Task:
        """Создаёт новую задачу с указанным типом."""
        task = Task(type=task_type, status="pending", progress=0, total=0)
        self._session.add(task)
        await self._session.flush()
        return task

    async def update_status(self, task_id: int, status: str) -> None:
        """Обновляет статус задачи."""
        await self._session.execute(
            update(Task).where(Task.id == task_id).values(status=status)
        )
        await self._session.flush()

    async def update_progress(
        self, task_id: int, progress: int, total: int | None = None
    ) -> None:
        """Обновляет прогресс задачи и опционально общее количество."""
        values: dict = {"progress": progress}
        if total is not None:
            values["total"] = total
        await self._session.execute(
            update(Task).where(Task.id == task_id).values(**values)
        )

    async def get_latest(self) -> Task | None:
        """Возвращает последнюю созданную задачу."""
        result = await self._session.execute(
            select(Task).order_by(Task.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, task_id: int) -> Task | None:
        """Возвращает задачу по первичному ключу."""
        return await self._session.get(Task, task_id)
