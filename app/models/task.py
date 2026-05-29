"""
Модель задачи — отслеживает выполнение фоновых операций парсинга и рассылки.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Task(Base):
    """
    Задача фонового выполнения.
    Позволяет отслеживать прогресс и управлять задачами через бота.
    """

    __tablename__ = "tasks"

    # Первичный ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Тип задачи:
    # "parse" — парсинг чатов/каналов
    # "send"  — массовая рассылка
    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Статус задачи:
    # "pending" — ожидает выполнения
    # "running" — выполняется прямо сейчас
    # "done"    — успешно завершена
    # "failed"  — завершена с ошибкой
    # "stopped" — остановлена пользователем
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="pending", index=True
    )

    # Текущий прогресс (количество обработанных элементов)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Общее количество элементов для обработки
    total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Время создания задачи
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    # Время последнего обновления статуса
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    def __repr__(self) -> str:
        return (
            f"<Task id={self.id} type={self.type!r} status={self.status!r} "
            f"progress={self.progress}/{self.total}>"
        )
