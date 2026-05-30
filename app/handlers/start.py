"""
Обработчики команд /start и /help.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.filters.admin_filter import AdminFilter
from app.keyboards.main import main_keyboard

# Роутер для команд запуска
router = Router()


@router.message(Command("start"), AdminFilter())
async def cmd_start(message: Message) -> None:
    """
    Обработчик команды /start.
    Показывает приветственное сообщение и главное меню.
    """
    await message.answer(
        "👋 <b>Добро пожаловать в Telegram Parser + Mass DM!</b>\n\n"
        "Это система для парсинга участников Telegram-чатов и рассылки сообщений.\n\n"
        "Используйте кнопки ниже для управления:",
        reply_markup=main_keyboard(),
        parse_mode="HTML",
    )


@router.message(Command("help"), AdminFilter())
async def cmd_help(message: Message) -> None:
    """
    Обработчик команды /help.
    Показывает список доступных команд.
    """
    help_text = (
        "📖 <b>Доступные команды:</b>\n\n"
        "/start — Главное меню\n"
        "/find — Начать парсинг по ключевым словам\n"
        "/status — Статус текущей задачи\n"
        "/stop — Остановить текущую задачу\n"
        "/stats — Статистика базы данных\n"
        "/accounts — Список аккаунтов и их статусы\n"
        "/send_test — Отправить тестовое сообщение\n"
        "/export_users — Скачать всех пользователей в JSON\n\n"
        "📁 <b>Конфигурация:</b>\n"
        "• <code>data/to_parse.json</code> — список каналов/групп для парсинга\n"
        "• <code>data/keywords.json</code> — ключевые слова для фильтрации\n"
        "• <code>data/message.txt</code> — текст рассылки\n"
        "• <code>sessions/</code> — файлы сессий аккаунтов (.session)\n"
        "• <code>media/</code> — медиафайл для рассылки (опционально)"
    )
    await message.answer(help_text, parse_mode="HTML")
