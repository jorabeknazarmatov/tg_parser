"""
Валидатор пользователей при парсинге.
Фильтрует ботов, удалённые аккаунты и пустые профили.
"""
from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telethon.types import User as TelegramUser


class UserValidator:
    """
    Проверяет пользователя на соответствие критериям для добавления в базу.
    Отфильтровывает нежелательные аккаунты.
    """

    def validate(
        self, user: "TelegramUser", chat_admins: set[int]
    ) -> bool:
        """
        Основной метод проверки пользователя.

        Args:
            user: Объект пользователя Telethon
            chat_admins: Множество ID администраторов чата

        Returns:
            True если пользователь подходит для добавления
        """
        # Отфильтровываем ботов
        if self.is_bot(user):
            return False
        # Отфильтровываем удалённые аккаунты
        if self.is_deleted(user):
            return False
        # Отфильтровываем "фейковые" пустые аккаунты
        if self.is_fake(user):
            return False
        # Отфильтровываем администраторов чата
        if self.is_admin(user, chat_admins):
            return False
        return True

    def is_bot(self, user: "TelegramUser") -> bool:
        """Проверяет, является ли пользователь ботом."""
        return bool(getattr(user, "bot", False))

    def is_deleted(self, user: "TelegramUser") -> bool:
        """Проверяет, удалён ли аккаунт."""
        return bool(getattr(user, "deleted", False))

    def is_fake(self, user: "TelegramUser") -> bool:
        """
        Проверяет, является ли аккаунт "пустым" (нет ни одного идентификатора).
        Такие аккаунты обычно не активны.
        """
        username = getattr(user, "username", None)
        first_name = getattr(user, "first_name", None)
        last_name = getattr(user, "last_name", None)
        return not any([username, first_name, last_name])

    def is_admin(self, user: "TelegramUser", admins: set[int]) -> bool:
        """Проверяет, является ли пользователь администратором чата."""
        return user.id in admins

    def make_hash(self, telegram_id: int, source_chat: str) -> str:
        """
        Создаёт уникальный хэш для комбинации telegram_id + source_chat.
        Используется для предотвращения дублей в базе данных.

        Args:
            telegram_id: Числовой ID пользователя Telegram
            source_chat: Username или ID источника

        Returns:
            SHA-256 хэш в виде hex-строки
        """
        raw = f"{telegram_id}:{source_chat.lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()
