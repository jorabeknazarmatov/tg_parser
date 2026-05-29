"""
Обработчик команды /status — показ статуса текущей задачи.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.filters.admin_filter import AdminFilter
from app.utils.helpers import format_progress_bar

if TYPE_CHECKING:
    from app.repositories.task_repo import TaskRepository

# Роутер для команды статуса
router = Router()

# Словарь для перевода статусов на русский
STATUS_RU = {
    "pending": "⏳ Ожидание",
    "running": "🔄 Выполняется",
    "done": "✅ Завершена",
    "failed": "❌ Ошибка",
    "stopped": "⏹ Остановлена",
}

# Словарь для перевода типов задач
TYPE_RU = {
    "parse": "🔍 Парсинг",
    "send": "📨 Рассылка",
}


@router.message(Command("status"), AdminFilter())
async def cmd_status(
    message: Message,
    task_repo: "TaskRepository",
) -> None:
    """
    Обработчик команды /status.
    Показывает статус последней задачи с прогресс-баром.
    """
    task = await task_repo.get_latest()

    if task is None:
        await message.answer(
            "📭 <b>Задач не найдено.</b>\n\n"
            "Используйте /find для запуска парсинга.",
            parse_mode="HTML",
        )
        return

    # Форматируем прогресс
    progress_bar = format_progress_bar(task.progress, task.total)
    pct = (
        int(task.progress / task.total * 100)
        if task.total > 0
        else 0
    )

    status_text = STATUS_RU.get(task.status, task.status)
    type_text = TYPE_RU.get(task.type, task.type)

    text = (
        f"📋 <b>Статус задачи #{task.id}</b>\n\n"
        f"Тип: {type_text}\n"
        f"Статус: {status_text}\n\n"
        f"Прогресс: {task.progress} / {task.total} ({pct}%)\n"
        f"{progress_bar}\n\n"
        f"Создана: {task.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"Обновлена: {task.updated_at.strftime('%d.%m.%Y %H:%M:%S')}"
    )

    await message.answer(text, parse_mode="HTML")
