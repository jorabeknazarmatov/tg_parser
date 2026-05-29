"""
Вспомогательные утилиты для форматирования и работы с данными.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Iterator, TypeVar

T = TypeVar("T")


def format_progress_bar(current: int, total: int, width: int = 20) -> str:
    """
    Форматирует прогресс-бар в виде строки Unicode.

    Args:
        current: Текущий прогресс
        total: Общее количество
        width: Ширина прогресс-бара в символах

    Returns:
        Строка вида: [████████░░░░░░░░░░░░] 40%

    Examples:
        >>> format_progress_bar(4, 10)
        '[████████░░░░░░░░░░░░] 40%'
    """
    if total <= 0:
        return f"[{'░' * width}] 0%"

    percent = min(current / total, 1.0)
    filled = int(width * percent)
    empty = width - filled

    bar = "█" * filled + "░" * empty
    pct = int(percent * 100)

    return f"[{bar}] {pct}%"


def format_timedelta(td: timedelta) -> str:
    """
    Форматирует timedelta в читаемую строку на русском языке.

    Args:
        td: Временной интервал

    Returns:
        Строка вида "2ч 30м 15с"
    """
    total_seconds = int(td.total_seconds())

    if total_seconds < 0:
        return "0с"

    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}ч")
    if minutes > 0:
        parts.append(f"{minutes}м")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}с")

    return " ".join(parts)


def chunk_list(lst: list[T], size: int) -> Iterator[list[T]]:
    """
    Разбивает список на чанки заданного размера.

    Args:
        lst: Исходный список
        size: Размер чанка

    Yields:
        Подсписки размером не более size

    Examples:
        >>> list(chunk_list([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]
    """
    for i in range(0, len(lst), size):
        yield lst[i : i + size]


def safe_username(user: object) -> str:
    """
    Возвращает безопасное отображаемое имя пользователя.
    Пробует username, потом first_name, потом telegram_id.

    Args:
        user: Объект пользователя (User model или Telethon User)

    Returns:
        Строковое представление пользователя
    """
    username = getattr(user, "username", None)
    if username:
        return f"@{username}"

    first_name = getattr(user, "first_name", None)
    last_name = getattr(user, "last_name", None)

    if first_name or last_name:
        parts = filter(None, [first_name, last_name])
        return " ".join(parts)

    telegram_id = getattr(user, "telegram_id", None) or getattr(user, "id", None)
    if telegram_id:
        return f"id:{telegram_id}"

    return "Неизвестный"
