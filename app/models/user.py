"""
Модель пользователя — найденный через парсер участник Telegram-чата/канала.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    """
    Хранит информацию о пользователях, собранных парсером.
    Поле unique_hash предотвращает дублирование одного юзера из одного источника.
    """

    __tablename__ = "users"

    # Первичный ключ
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Telegram ID пользователя (bigint для поддержки больших чисел)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    # Имя пользователя без @
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Имя
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Фамилия
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Номер телефона (если доступен)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Источник — username чата/канала
    source_chat: Mapped[str] = mapped_column(String(255), nullable=False)

    # Ключевое слово, по которому найден пользователь
    matched_keyword: Mapped[str] = mapped_column(String(255), nullable=False)

    # Дата последней активности пользователя в источнике
    last_activity_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Время парсинга
    parsed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )

    # Было ли сообщение отправлено
    is_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Была ли ошибка при отправке
    is_failed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Количество неудачных попыток отправки
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Уникальный хэш: md5(telegram_id + source_chat) — защита от дублей
    unique_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    __table_args__ = (
        Index("ix_users_unique_hash", "unique_hash", unique=True),
        Index("ix_users_is_sent_is_failed", "is_sent", "is_failed"),
    )

    def __repr__(self) -> str:
        return (
            f"<User id={self.id} telegram_id={self.telegram_id} "
            f"username={self.username!r} source={self.source_chat!r}>"
        )
