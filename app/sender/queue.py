"""
Очередь пользователей для массовой рассылки.
Использует asyncio.Queue для потокобезопасной работы.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.user import User


class SendQueue:
    """
    Асинхронная очередь пользователей для отправки сообщений.
    Потокобезопасна для использования с несколькими воркерами.
    """

    def __init__(self, maxsize: int = 1000) -> None:
        # Внутренняя очередь asyncio
        self._queue: asyncio.Queue["User"] = asyncio.Queue(maxsize=maxsize)

    async def enqueue(self, user: "User") -> None:
        """
        Добавляет пользователя в очередь.
        Блокируется если очередь переполнена.

        Args:
            user: Пользователь для добавления в очередь
        """
        await self._queue.put(user)

    async def dequeue(self) -> "User":
        """
        Извлекает следующего пользователя из очереди.
        Блокируется если очередь пуста.

        Returns:
            Следующий пользователь в очереди
        """
        return await self._queue.get()

    def task_done(self) -> None:
        """Помечает задачу как выполненную (для join())."""
        self._queue.task_done()

    def size(self) -> int:
        """Возвращает текущий размер очереди."""
        return self._queue.qsize()

    def is_empty(self) -> bool:
        """Возвращает True если очередь пуста."""
        return self._queue.empty()

    def is_full(self) -> bool:
        """Возвращает True если очередь переполнена."""
        return self._queue.full()

    async def join(self) -> None:
        """Ожидает обработки всех элементов очереди."""
        await self._queue.join()
