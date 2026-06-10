"""
Обработчик команды /send_test — отправка тестового сообщения.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from app.core.logging import get_logger
from app.filters.admin_filter import AdminFilter

if TYPE_CHECKING:
    from app.core.account_manager import AccountManager
    from app.core.config import Settings

logger = get_logger("bot")

# Роутер для тестовой команды
router = Router()

async def execute_send_test_logic(status_msg: Message, account_manager: "AccountManager", admin_id: int) -> None:
    # Получаем доступный клиент
    client_data = await account_manager.get_available_client()
    if client_data is None:
        await status_msg.edit_text(
            "❌ <b>Нет доступных аккаунтов.</b>\n\n"
            "Проверьте наличие .session файлов в директории sessions/",
            parse_mode="HTML",
        )
        return

    client, account = client_data
    try:
        # Загружаем текст сообщения
        import aiofiles
        from pathlib import Path

        message_path = Path("data/message.txt")
        if message_path.exists():
            async with aiofiles.open(message_path, encoding="utf-8") as f:
                text = await f.read()
        else:
            text = "✅ Тестовое сообщение от Telegram Parser!\nСистема работает корректно."

        # Отправляем сообщение администратору
        admin_id = status_msg.from_user.id
        await client.send_message(admin_id, text.strip())

        await status_msg.edit_text(
            f"✅ <b>Тестовое сообщение отправлено!</b>\n\n"
            f"Аккаунт: <code>{account.session_name}</code>\n"
            f"Получатель: вы (ID: {admin_id})",
            parse_mode="HTML",
        )

        logger.info(
            "Тестовое сообщение отправлено",
            account=account.session_name,
            admin_id=admin_id,
        )

    except Exception as exc:
        logger.error("Ошибка отправки тестового сообщения", error=str(exc))
        await status_msg.edit_text(
            f"❌ <b>Ошибка отправки:</b>\n<code>{exc}</code>",
            parse_mode="HTML",
        )
    finally:
        account_manager.release_client(account.session_name)


@router.message(Command("send_test"), AdminFilter())
async def cmd_send_test(
    message: Message,
    account_manager: "AccountManager",
) -> None:
    """
    Обработчик команды /send_test.
    Отправляет тестовое сообщение администратору через первый доступный аккаунт.
    """
    status_msg = await message.answer(
        "🔄 <b>Отправляю тестовое сообщение...</b>",
        parse_mode="HTML",
    )
    admin_id = message.from_user.id

    await execute_send_test_logic(status_msg, account_manager, admin_id)


# Обработчик для кнопки "Отправить тестовое сообщение" в главном меню
@router.callback_query(F.data == "test_run", AdminFilter())
async def callback_send_test(query: CallbackQuery, account_manager: "AccountManager") -> None:
    await query.answer()
    status_msg = await query.message.edit_text(
        "🔄 <b>Отправляю тестовое сообщение...</b>",
        parse_mode="HTML",
    )
    admin_id = query.from_user.id

    await execute_send_test_logic(status_msg, account_manager, admin_id)