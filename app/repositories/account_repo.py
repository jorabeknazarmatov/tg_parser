"""
Репозиторий для работы с аккаунтами Telegram в базе данных.
Управляет статусами, лимитами и FloodWait аккаунтов.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account


class AccountRepository:
    """Репозиторий для управления Telegram аккаунтами."""

    def __init__(self, session: AsyncSession, max_per_account: int = 40) -> None:
        # Сессия базы данных
        self._session = session
        # Максимальное количество отправок с одного аккаунта в день
        self._max_per_account = max_per_account

    async def get_all(self) -> list[Account]:
        """Возвращает все аккаунты из базы данных."""
        result = await self._session.execute(
            select(Account).order_by(Account.session_name)
        )
        return list(result.scalars().all())

    async def get_active(self) -> list[Account]:
        """
        Возвращает доступные для отправки аккаунты.
        Фильтрует: статус active, не превышен лимит отправок,
        FloodWait истёк или не установлен.
        """
        now = datetime.now(tz=timezone.utc)
        result = await self._session.execute(
            select(Account).where(
                Account.status == "active",
                Account.sent_today < self._max_per_account,
                (Account.flood_until == None) | (Account.flood_until <= now),  # noqa: E711
            )
        )
        return list(result.scalars().all())

    async def get_by_name(self, session_name: str) -> Account | None:
        """Возвращает аккаунт по имени сессии."""
        result = await self._session.execute(
            select(Account).where(Account.session_name == session_name)
        )
        return result.scalar_one_or_none()

    async def create_or_update(self, session_name: str) -> Account:
        """
        Создаёт новый аккаунт или возвращает существующий.
        Используется при загрузке .session файлов.
        """
        stmt = (
            insert(Account)
            .values(
                session_name=session_name,
                status="active",
                sent_today=0,
                total_sent=0,
                last_reset=func.now(),
            )
            .on_conflict_do_nothing(index_elements=["session_name"])
        )
        await self._session.execute(stmt)
        await self._session.flush()

        # Получаем актуальную запись
        result = await self._session.execute(
            select(Account).where(Account.session_name == session_name)
        )
        return result.scalar_one()

    async def set_flood(self, account_id: int, seconds: int) -> None:
        """
        Устанавливает FloodWait для аккаунта на указанное количество секунд.
        Меняет статус на 'flood'.
        """
        from datetime import timedelta

        flood_until = datetime.now(tz=timezone.utc) + timedelta(seconds=seconds)
        await self._session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(status="flood", flood_until=flood_until)
        )

    async def set_disabled(self, account_id: int) -> None:
        """Отключает аккаунт (например, при получении PeerFloodError)."""
        await self._session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(status="disabled")
        )

    async def increment_sent(self, account_id: int) -> None:
        """Увеличивает счётчики отправленных сообщений."""
        await self._session.execute(
            update(Account)
            .where(Account.id == account_id)
            .values(
                sent_today=Account.sent_today + 1,
                total_sent=Account.total_sent + 1,
                last_used=func.now(),
            )
        )

    async def reset_daily_counts(self) -> None:
        """
        Сбрасывает суточные счётчики отправок для всех аккаунтов.
        Также снимает статус 'flood' если время FloodWait истекло.
        """
        now = datetime.now(tz=timezone.utc)

        # Сброс суточных счётчиков
        await self._session.execute(
            update(Account).values(sent_today=0, last_reset=func.now())
        )

        # Снятие статуса flood у истёкших аккаунтов
        await self._session.execute(
            update(Account)
            .where(
                Account.status == "flood",
                Account.flood_until != None,  # noqa: E711
                Account.flood_until <= now,
            )
            .values(status="active", flood_until=None)
        )

    async def check_and_clear_flood(self) -> int:
        """
        Проверяет и снимает истёкшие FloodWait.
        Возвращает количество восстановленных аккаунтов.
        """
        now = datetime.now(tz=timezone.utc)
        result = await self._session.execute(
            update(Account)
            .where(
                Account.status == "flood",
                Account.flood_until != None,  # noqa: E711
                Account.flood_until <= now,
            )
            .values(status="active", flood_until=None)
            .returning(Account.id)
        )
        rows = result.fetchall()
        return len(rows)
