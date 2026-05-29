"""
Репозиторий для работы с пользователями в базе данных.
Реализует все операции CRUD и агрегирующие запросы для модели User.
"""
from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    """Репозиторий для управления записями пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        # Сессия базы данных
        self._session = session

    async def get_by_hash(self, unique_hash: str) -> User | None:
        """Возвращает пользователя по уникальному хэшу (telegram_id + source_chat)."""
        result = await self._session.execute(
            select(User).where(User.unique_hash == unique_hash)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: int) -> User | None:
        """Возвращает пользователя по первичному ключу."""
        return await self._session.get(User, user_id)

    async def create(self, user_data: dict) -> User:
        """Создаёт нового пользователя из словаря данных."""
        user = User(**user_data)
        self._session.add(user)
        await self._session.flush()
        return user

    async def bulk_create(self, users: list[dict]) -> int:
        """
        Массово создаёт пользователей, пропуская дубликаты по unique_hash.
        Возвращает количество реально добавленных записей.
        """
        if not users:
            return 0

        # Используем INSERT OR IGNORE для SQLite
        stmt = insert(User).prefix_with("OR IGNORE")
        await self._session.execute(stmt, users)
        await self._session.flush()

        # Получаем актуальное количество совпадающих хэшей
        hashes = [u["unique_hash"] for u in users]
        result = await self._session.execute(
            select(func.count()).where(User.unique_hash.in_(hashes))
        )
        return result.scalar_one()

    async def get_unsent(self, limit: int = 100) -> list[User]:
        """Возвращает список пользователей которым ещё не отправлено сообщение."""
        result = await self._session.execute(
            select(User)
            .where(User.is_sent == False, User.is_failed == False)  # noqa: E712
            .order_by(User.parsed_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_sent(self, user_id: int) -> None:
        """Помечает пользователя как успешно получившего сообщение."""
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_sent=True, is_failed=False)
        )

    async def mark_failed(self, user_id: int, error: str) -> None:
        """
        Помечает пользователя как неудачного после превышения попыток.
        Увеличивает счётчик неудач.
        """
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(
                is_failed=True,
                fail_count=User.fail_count + 1,
            )
        )

    async def increment_fail_count(self, user_id: int) -> None:
        """Увеличивает счётчик неудачных попыток без окончательной пометки."""
        await self._session.execute(
            update(User)
            .where(User.id == user_id)
            .values(fail_count=User.fail_count + 1)
        )

    async def count_total(self) -> int:
        """Возвращает общее количество пользователей в базе."""
        result = await self._session.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def count_sent(self) -> int:
        """Возвращает количество пользователей которым отправлено сообщение."""
        result = await self._session.execute(
            select(func.count()).where(User.is_sent == True)  # noqa: E712
        )
        return result.scalar_one()

    async def count_failed(self) -> int:
        """Возвращает количество пользователей с ошибками отправки."""
        result = await self._session.execute(
            select(func.count()).where(User.is_failed == True)  # noqa: E712
        )
        return result.scalar_one()

    async def count_unsent(self) -> int:
        """Возвращает количество пользователей ожидающих отправки."""
        result = await self._session.execute(
            select(func.count()).where(
                User.is_sent == False, User.is_failed == False  # noqa: E712
            )
        )
        return result.scalar_one()
