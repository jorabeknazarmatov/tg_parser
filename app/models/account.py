"""
Модель аккаунта Telegram для отправки сообщений.
Каждый аккаунт соответствует .session файлу в директории sessions/.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Account(Base):
    """
    Хранит состояние каждого Telegram-аккаунта используемого для рассылки.
    Управляет лимитами и статусами FloodWait.
    """

    __tablename__ = "accounts"

    # Первичный ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Имя сессии (без расширения .session)
    session_name: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )

    # Статус аккаунта:
    # "active"   — готов к работе
    # "disabled" — отключён вручную или из-за ошибок
    # "flood"    — временная блокировка от Telegram
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="active", index=True
    )

    # Время до которого аккаунт в режиме FloodWait
    flood_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Количество отправленных сообщений сегодня
    sent_today: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Всего отправлено за всё время
    total_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Дата последнего использования
    last_used: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Дата последнего сброса суточных счётчиков
    last_reset: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<Account id={self.id} session={self.session_name!r} "
            f"status={self.status!r} sent_today={self.sent_today}>"
        )
