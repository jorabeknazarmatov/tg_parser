"""
Репозиторий для работы с журналом отправки сообщений.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.send_log import SendLog


class SendLogRepository:
    """Репозиторий для записи и чтения логов отправки."""

    def __init__(self, session: AsyncSession) -> None:
        # Сессия базы данных
        self._session = session

    async def create(
        self,
        user_id: int,
        account_id: int,
        status: str,
        error: str | None = None,
    ) -> SendLog:
        """Создаёт запись лога для попытки отправки сообщения."""
        log = SendLog(
            user_id=user_id,
            account_id=account_id,
            status=status,
            error=error,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def count_flood(self) -> int:
        """Возвращает количество записей со статусом flood."""
        result = await self._session.execute(
            select(func.count()).where(SendLog.status == "flood")
        )
        return result.scalar_one()

    async def count_by_status(self, status: str) -> int:
        """Возвращает количество записей с указанным статусом."""
        result = await self._session.execute(
            select(func.count()).where(SendLog.status == status)
        )
        return result.scalar_one()

    async def get_recent(self, limit: int = 50) -> list[SendLog]:
        """Возвращает последние записи лога."""
        result = await self._session.execute(
            select(SendLog).order_by(SendLog.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())
