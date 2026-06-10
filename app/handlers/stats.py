"""
Обработчик команды /stats — статистика системы.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app.filters.admin_filter import AdminFilter
from app.services import stats_service
from app.utils.helpers import format_progress_bar

if TYPE_CHECKING:
    from app.services.stats_service import StatsService

# Роутер для команды статистики
router = Router()

# Text для команды /stats
async def stats_text(stats_service: "StatsService") -> str:
    stats = await stats_service.get_full_stats()

    total = stats.get("total_users", 0)
    sent = stats.get("sent_users", 0)
    failed = stats.get("failed_users", 0)
    unsent = stats.get("unsent_users", 0)

    # Прогресс бар по отправленным
    progress_bar = format_progress_bar(sent, total) if total > 0 else "[нет данных]"

    # Статистика аккаунтов
    active_accounts = stats.get("active_accounts", 0)
    flood_accounts = stats.get("flood_accounts", 0)
    disabled_accounts = stats.get("disabled_accounts", 0)
    total_accounts = stats.get("total_accounts", 0)

    # Статистика задач
    last_task = stats.get("last_task")
    task_info = ""
    if last_task:
        task_info = (
            f"\n\n📋 <b>Последняя задача:</b>\n"
            f"• Тип: {last_task.get('type', 'N/A')}\n"
            f"• Статус: {last_task.get('status', 'N/A')}\n"
            f"• Прогресс: {last_task.get('progress', 0)}/{last_task.get('total', 0)}"
        )

    text = (
        "📊 <b>Статистика системы</b>\n"
        "─────────────────────\n"
        f"👥 <b>Пользователи:</b>\n"
        f"• Всего: <b>{total}</b>\n"
        f"• Отправлено: <b>{sent}</b>\n"
        f"• Ошибки: <b>{failed}</b>\n"
        f"• Ожидают: <b>{unsent}</b>\n"
        f"{progress_bar}\n\n"
        f"👤 <b>Аккаунты:</b>\n"
        f"• Всего: <b>{total_accounts}</b>\n"
        f"• Активных: <b>{active_accounts}</b>\n"
        f"• FloodWait: <b>{flood_accounts}</b>\n"
        f"• Отключено: <b>{disabled_accounts}</b>"
        f"{task_info}"
    )

    return text

# Обработчик для команды /stats
@router.message(Command("stats"), AdminFilter())
async def cmd_stats(message: Message, stats_service: "StatsService",) -> None:
    text = await stats_text(stats_service)
    await message.answer(text, parse_mode="HTML")

# Обработчик для обновления статистики по кнопке
@router.callback_query(F.data == "stats", AdminFilter())
async def callback_stats(query: CallbackQuery, stats_service: "StatsService",) -> None:
    text = await stats_text(stats_service)
    await query.message.edit_text(text, parse_mode="HTML")
