"""
Фильтр для проверки прав администратора в боте.
"""
from __future__ import annotations

from aiogram import types
from aiogram.filters import BaseFilter

from app.core.config import Settings


class AdminFilter(BaseFilter):
    """
    Фильтр aiogram 3: пропускает только сообщения от администраторов.
    Список администраторов берётся из настроек ADMIN_IDS.
    """

    async def __call__(
        self,
        message: types.Message,
        settings: Settings,
    ) -> bool:
        """
        Проверяет, является ли отправитель администратором.

        Args:
            message: Входящее сообщение
            settings: Настройки приложения (через DI)

        Returns:
            True если пользователь есть в ADMIN_IDS
        """
        if message.from_user is None:
            return False
        return message.from_user.id in settings.ADMIN_IDS
