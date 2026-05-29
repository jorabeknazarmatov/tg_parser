"""
Модель лога отправки — фиксирует каждую попытку отправки сообщения.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SendLog(Base):
    """
    Журнал всех попыток отправки сообщений.
    Связан с пользователем и аккаунтом отправителя.
    """

    __tablename__ = "send_logs"

    # Первичный ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Ссылка на пользователя которому отправлялось сообщение
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Ссылка на аккаунт который отправлял
    account_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=False,
        index=True,
    )

    # Статус попытки:
    # "sent"  — успешно отправлено
    # "failed"— ошибка отправки
    # "flood" — FloodWait от Telegram
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    # Текст ошибки если статус "failed" или "flood"
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Время записи лога
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<SendLog id={self.id} user_id={self.user_id} "
            f"account_id={self.account_id} status={self.status!r}>"
        )
