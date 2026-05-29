"""
Конфигурация Alembic для асинхронных миграций базы данных.
Поддерживает async SQLAlchemy через aiosqlite.
"""
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Получаем конфигурацию alembic
config = context.config

# Настраиваем логирование из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Импортируем Base и все модели для автогенерации миграций
from app.db.base import Base
import app.models  # noqa: F401 — регистрация всех моделей в метаданных

# Метаданные для автогенерации миграций
target_metadata = Base.metadata

# Загружаем URL из настроек приложения
try:
    from app.core.config import settings
    config.set_main_option("sqlalchemy.url", settings.DB_URL)
except Exception:
    # Если настройки недоступны, используем URL из alembic.ini
    pass


def run_migrations_offline() -> None:
    """
    Запускает миграции в offline-режиме (без подключения к БД).
    Используется для генерации SQL-скриптов.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Запускает миграции через указанное соединение.

    Args:
        connection: Соединение SQLAlchemy
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Запускает миграции асинхронно через aiosqlite."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Запускает миграции в online-режиме (с подключением к БД)."""
    asyncio.run(run_async_migrations())


# Выбираем режим запуска миграций
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
