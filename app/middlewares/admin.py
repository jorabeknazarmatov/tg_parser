"""
Middleware для логирования активности пользователей бота.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message

from app.core.logging import get_logger

logger = get_logger("bot")


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования всех входящих сообщений в боте.
    Записывает ID пользователя, имя и текст команды.
    """

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        """
        Перехватывает сообщение, логирует и передаёт дальше.

        Args:
            handler: Следующий обработчик в цепочке
            event: Входящее сообщение
            data: Данные middleware

        Returns:
            Результат обработки
        """
        if isinstance(event, Message) and event.from_user:
            logger.info(
                "Команда бота получена",
                user_id=event.from_user.id,
                username=event.from_user.username,
                text=event.text,
            )

        result = await handler(event, data)
        return result
