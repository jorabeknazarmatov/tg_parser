"""
Асинхронный движок SQLAlchemy и фабрика сессий.
Поддерживает SQLite через aiosqlite.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base

# Глобальные объекты движка и фабрики сессий
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Возвращает глобальный движок базы данных."""
    if _engine is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db() сначала.")
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Возвращает глобальную фабрику сессий."""
    if _session_factory is None:
        raise RuntimeError("База данных не инициализирована. Вызовите init_db() сначала.")
    return _session_factory


async def init_db(db_url: str) -> None:
    """
    Инициализирует движок базы данных и создаёт все таблицы.

    Args:
        db_url: Строка подключения к БД (например sqlite+aiosqlite:///data/tg_parser.db)
    """
    global _engine, _session_factory

    # Создаём директорию data/ если нужно
    if db_url.startswith("sqlite"):
        db_path_str = db_url.replace("sqlite+aiosqlite:///", "")
        db_path = Path(db_path_str)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    # Создаём асинхронный движок
    _engine = create_async_engine(
        db_url,
        echo=False,  # Отключаем SQL-логи в продакшене
        pool_pre_ping=True,  # Проверяем соединение перед использованием
    )

    # Фабрика сессий с автоматическим управлением транзакциями
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )

    # Импортируем все модели чтобы Base знала о них
    import app.models  # noqa: F401

    # Создаём все таблицы
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Асинхронный генератор сессий для использования как dependency injection.
    Автоматически закрывает сессию и откатывает транзакцию при ошибке.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """Закрывает движок базы данных при завершении приложения."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
