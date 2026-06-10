"""
Обработчик команды /status — показ статуса текущей задачи.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

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

async def text_status(task_repo: "TaskRepository") -> str:
    task = await task_repo.get_latest()

    if task is None:
        return "📭 <b>Задач не найдено.</b>"

    # Форматируем прогресс
    progress_bar = format_progress_bar(task.progress, task.total)
    pct = (
        int(task.progress / task.total * 100)
        if task.total > 0
        else 0
    )

    status_text = STATUS_RU.get(task.status, task.status)
    type_text = TYPE_RU.get(task.type, task.type)

    return (
        f"📋 <b>Статус задачи #{task.id}</b>\n\n"
        f"Тип: {type_text}\n"
        f"Статус: {status_text}\n\n"
        f"Прогресс: {task.progress} / {task.total} ({pct}%)\n"
        f"{progress_bar}\n\n"
        f"Создана: {task.created_at.strftime('%d.%m.%Y %H:%M:%S')}\n"
        f"Обновлена: {task.updated_at.strftime('%d.%m.%Y %H:%M:%S')}"
    )

@router.message(Command("status"), AdminFilter())
async def cmd_status(
    message: Message,
    task_repo: "TaskRepository",
) -> None:
    """
    Обработчик команды /status.
    Показывает статус последней задачи с прогресс-баром.
    """
    text = await text_status(task_repo)
    await message.answer(text, parse_mode="HTML")

# Обработчик для кнопки "Показать статус" в главном меню
@router.callback_query(F.data == "task_status", AdminFilter())
async def callback_status(query: CallbackQuery, task_repo: "TaskRepository") -> None:
    await query.answer()
    text = await text_status(task_repo)
    await query.message.edit_text(text, parse_mode="HTML")
