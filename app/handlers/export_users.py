"""
Обработчик команды /export_users — экспорт всех пользователей в JSON-файл.
"""
from __future__ import annotations

import io
import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import BufferedInputFile, Message

from app.filters.admin_filter import AdminFilter

if TYPE_CHECKING:
    from app.repositories.user_repo import UserRepository

router = Router()


@router.message(Command("export_users"), AdminFilter())
async def cmd_export_users(
    message: Message,
    user_repo: "UserRepository",
) -> None:
    """
    Обработчик команды /export_users.
    Формирует all_users.json из базы данных и отправляет файл в чат.
    """
    status_msg = await message.answer("⏳ <b>Формирую экспорт...</b>", parse_mode="HTML")

    users = await user_repo.get_all_for_export()

    if not users:
        await status_msg.edit_text("📭 <b>Пользователей в базе нет.</b>", parse_mode="HTML")
        return

    # Формируем список словарей для JSON
    export_data = []
    for u in users:
        # Полное имя
        name_parts = [u.first_name or "", u.last_name or ""]
        full_name = " ".join(p for p in name_parts if p).strip() or None

        export_data.append({
            "user_id":       u.telegram_id,
            "name":          full_name,
            "tg_username":   f"@{u.username}" if u.username else None,
            "get_in_channel": u.source_chat,
            "matched_keyword": u.matched_keyword,
            "message":       u.message_text,
            "is_sent":       u.is_sent,
            "parsed_at":     u.parsed_at.strftime("%Y-%m-%d %H:%M:%S") if u.parsed_at else None,
        })

    # Сериализуем в JSON
    json_bytes = json.dumps(
        export_data,
        ensure_ascii=False,
        indent=2,
    ).encode("utf-8")

    # Имя файла с датой
    filename = f"users_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"

    await status_msg.delete()
    await message.answer_document(
        document=BufferedInputFile(json_bytes, filename=filename),
        caption=(
            f"📦 <b>Экспорт пользователей</b>\n\n"
            f"• Всего: <b>{len(export_data)}</b>\n"
            f"• Отправлено: <b>{sum(1 for u in export_data if u['is_sent'])}</b>\n"
            f"• Ожидают: <b>{sum(1 for u in export_data if not u['is_sent'])}</b>"
        ),
        parse_mode="HTML",
    )
