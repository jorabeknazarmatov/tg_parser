"""
Обработчик команды /stop — остановка текущей задачи.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.filters.admin_filter import AdminFilter
from app.keyboards.main import confirm_keyboard

if TYPE_CHECKING:
    from app.services.parser_service import ParserService
    from app.services.sender_service import SenderService
    from app.repositories.task_repo import TaskRepository

# Роутер для команды остановки
router = Router()


@router.message(Command("stop"), AdminFilter())
async def cmd_stop(
    message: Message,
    task_repo: "TaskRepository",
) -> None:
    """
    Обработчик команды /stop.
    Запрашивает подтверждение перед остановкой задачи.
    """
    active_task = await task_repo.get_active()

    if active_task is None:
        await message.answer(
            "📭 <b>Нет активных задач для остановки.</b>",
            parse_mode="HTML",
        )
        return

    type_ru = {"parse": "парсинг", "send": "рассылку"}.get(active_task.type, active_task.type)

    await message.answer(
        f"⚠️ <b>Вы уверены, что хотите остановить {type_ru}?</b>\n\n"
        f"Задача #{active_task.id} сейчас выполняется.\n"
        f"Прогресс: {active_task.progress}/{active_task.total}",
        reply_markup=confirm_keyboard("stop"),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "confirm:stop")
async def callback_confirm_stop(
    callback: CallbackQuery,
    parser_service: "ParserService",
    sender_service: "SenderService",
    task_repo: "TaskRepository",
) -> None:
    """
    Обработчик подтверждения остановки задачи.
    Останавливает активную задачу парсинга или рассылки.
    """
    active_task = await task_repo.get_active()

    if active_task is None:
        await callback.message.edit_text("📭 Задача уже завершена.")
        await callback.answer()
        return

    # Останавливаем нужный сервис
    if active_task.type == "parse":
        await parser_service.stop_parse_task()
    elif active_task.type == "send":
        await sender_service.stop_send_task()

    await callback.message.edit_text(
        f"⏹ <b>Задача #{active_task.id} остановлена.</b>",
        parse_mode="HTML",
    )
    await callback.answer("Задача остановлена")


@router.callback_query(F.data == "cancel")
async def callback_cancel(callback: CallbackQuery) -> None:
    """Обработчик отмены действия."""
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.answer("Отменено")
