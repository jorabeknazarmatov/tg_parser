"""
Обработчик команды /find — запуск парсинга.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.core.logging import get_logger
from app.filters.admin_filter import AdminFilter

if TYPE_CHECKING:
    from app.services.parser_service import ParserService
    from app.repositories.task_repo import TaskRepository

logger = get_logger("bot")

# Роутер для команды парсинга
router = Router()


@router.message(Command("find"), AdminFilter())
async def cmd_find(
    message: Message,
    parser_service: "ParserService",
    task_repo: "TaskRepository",
) -> None:
    """
    Обработчик команды /find.
    Запускает парсинг всех источников из to_parse.json.
    """
    # Проверяем, нет ли активной задачи
    active_task = await task_repo.get_active()
    if active_task:
        await message.answer(
            f"⚠️ Уже выполняется задача <b>{active_task.type}</b> "
            f"(статус: {active_task.status})\n\n"
            "Используйте /stop для остановки.",
            parse_mode="HTML",
        )
        return

    # Создаём задачу и запускаем парсинг
    status_msg = await message.answer(
        "🔍 <b>Запускаю парсинг...</b>\n\n"
        "Загружаю список источников и ключевые слова.",
        parse_mode="HTML",
    )

    try:
        task = await parser_service.start_parse_task()

        await status_msg.edit_text(
            f"✅ <b>Парсинг запущен!</b>\n\n"
            f"ID задачи: <code>{task.id}</code>\n"
            "Используйте /status для проверки прогресса.",
            parse_mode="HTML",
        )

        logger.info(
            "Парсинг запущен через бота",
            task_id=task.id,
            user_id=message.from_user.id if message.from_user else None,
        )

    except FileNotFoundError as exc:
        await status_msg.edit_text(
            f"❌ <b>Ошибка:</b> {exc}\n\n"
            "Убедитесь, что файлы <code>data/to_parse.json</code> и "
            "<code>data/keywords.json</code> существуют.",
            parse_mode="HTML",
        )
    except Exception as exc:
        logger.error("Ошибка запуска парсинга", error=str(exc))
        await status_msg.edit_text(
            f"❌ <b>Ошибка запуска парсинга:</b>\n<code>{exc}</code>",
            parse_mode="HTML",
        )
