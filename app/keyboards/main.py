"""
Инлайн-клавиатуры для Telegram-бота.
"""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт главное меню бота с основными командами.

    Returns:
        Инлайн-клавиатура с кнопками действий
    """
    builder = InlineKeyboardBuilder()

    # Кнопки основных действий
    builder.add(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🔍 Начать парсинг", callback_data="start_parse"),
        InlineKeyboardButton(text="📨 Начать рассылку", callback_data="start_send"),
        InlineKeyboardButton(text="⏹ Остановить", callback_data="stop"),
        InlineKeyboardButton(text="👤 Аккаунты", callback_data="accounts"),
        InlineKeyboardButton(text="📋 Статус задачи", callback_data="task_status"),
    )

    # Размещаем по 2 кнопки в строке
    builder.adjust(2)

    return builder.as_markup()


def confirm_keyboard(action: str) -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру подтверждения действия.

    Args:
        action: Идентификатор действия для callback_data

    Returns:
        Клавиатура с кнопками "Подтвердить" и "Отмена"
    """
    builder = InlineKeyboardBuilder()

    builder.add(
        InlineKeyboardButton(
            text="✅ Подтвердить",
            callback_data=f"confirm:{action}",
        ),
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel",
        ),
    )

    builder.adjust(2)

    return builder.as_markup()


def back_keyboard() -> InlineKeyboardMarkup:
    """
    Создаёт клавиатуру с кнопкой возврата в главное меню.

    Returns:
        Клавиатура с кнопкой "Назад"
    """
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="◀️ Главное меню", callback_data="main_menu"))
    return builder.as_markup()
