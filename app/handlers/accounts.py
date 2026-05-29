"""
Обработчик команды /accounts — список аккаунтов и их статусы.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.filters.admin_filter import AdminFilter

if TYPE_CHECKING:
    from app.core.account_manager import AccountManager

# Роутер для команды аккаунтов
router = Router()


@router.message(Command("accounts"), AdminFilter())
async def cmd_accounts(
    message: Message,
    account_manager: "AccountManager",
) -> None:
    """
    Обработчик команды /accounts.
    Показывает таблицу статусов всех аккаунтов.
    """
    statuses = await account_manager.get_all_status()

    if not statuses:
        await message.answer(
            "📭 <b>Аккаунты не найдены.</b>\n\n"
            "Добавьте .session файлы в директорию <code>sessions/</code>",
            parse_mode="HTML",
        )
        return

    lines = ["👤 <b>Аккаунты:</b>\n"]

    for acc in statuses:
        name = acc["session_name"]
        status = acc["status"]
        sent_today = acc["sent_today"]
        total_sent = acc["total_sent"]
        is_connected = acc["is_connected"]
        flood_until = acc.get("flood_until")

        # Иконки статусов
        status_icon = {
            "active": "🟢",
            "flood": "🟡",
            "disabled": "🔴",
        }.get(status, "⚪")

        conn_icon = "🔗" if is_connected else "🔌"

        # Информация о FloodWait
        flood_info = ""
        if flood_until:
            now = datetime.now(tz=timezone.utc)
            if flood_until.tzinfo is None:
                flood_until = flood_until.replace(tzinfo=timezone.utc)
            if flood_until > now:
                remaining = int((flood_until - now).total_seconds())
                flood_info = f" (ещё {remaining}с)"

        lines.append(
            f"{status_icon} {conn_icon} <code>{name}</code>\n"
            f"   Сегодня: {sent_today} | Всего: {total_sent}{flood_info}"
        )

    await message.answer("\n".join(lines), parse_mode="HTML")
