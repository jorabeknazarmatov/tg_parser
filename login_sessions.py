"""
Скрипт авторизации Telegram-аккаунтов из userbot.json.
Запускать один раз перед запуском основного бота.

Использование:
    python login_sessions.py
"""
from __future__ import annotations

import asyncio
import json
import os

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError


USERBOT_JSON_PATH = os.path.join("sessions", "userbot.json")


def load_userbot_json() -> dict:
    """Загружает конфигурацию аккаунтов из userbot.json."""
    if not os.path.exists(USERBOT_JSON_PATH):
        raise FileNotFoundError(
            f"Файл {USERBOT_JSON_PATH} не найден. "
            "Создайте его по образцу из документации."
        )
    with open(USERBOT_JSON_PATH, encoding="utf-8") as f:
        return json.load(f)


async def login_user(username: str, user_info: dict) -> TelegramClient | None:
    """
    Авторизует один аккаунт Telegram.
    Если сессия уже существует и действительна — просто подключается.
    При отсутствии сессии запрашивает код подтверждения и при необходимости 2FA-пароль.

    Args:
        username: Ключ пользователя из userbot.json (например "1", "2")
        user_info: Словарь с полями number, api_id, api_hash, session

    Returns:
        Подключённый TelegramClient или None при ошибке
    """
    print(f"\n{'─' * 40}")
    print(f"🔄 Авторизация аккаунта user_{username}...")

    phone    = user_info["number"]
    api_id   = int(user_info["api_id"])
    api_hash = user_info["api_hash"]
    session_name = user_info.get("session", f"user_{username}")

    # Путь к файлу сессии (sessions/user_1.session и т.д.)
    session_path = os.path.join("sessions", session_name)

    client = TelegramClient(session_path, api_id, api_hash)

    # Подключаемся к серверам Telegram
    try:
        await client.connect()
    except Exception as e:
        print(f"❌ Не удалось подключиться для {phone}: {e}")
        return None

    # Проверяем, авторизован ли уже аккаунт
    if await client.is_user_authorized():
        print(f"✅ Аккаунт {phone} уже авторизован, пропускаем.")
        return client

    # Отправляем код подтверждения
    try:
        print(f"📲 Отправляем код подтверждения на {phone}...")
        await client.send_code_request(phone)

        code = input(f"🔑 Введите код подтверждения для {phone}: ").strip()

        try:
            await client.sign_in(phone, code)
        except SessionPasswordNeededError:
            # Включена двухфакторная аутентификация
            password = input(f"🔒 Введите 2FA-пароль для {phone}: ").strip()
            await client.sign_in(password=password)

    except Exception as e:
        print(f"❌ Ошибка входа в аккаунт user_{username} ({phone}): {e}")
        await client.disconnect()
        return None

    print(f"✅ Успешный вход в аккаунт {phone}!")
    return client


async def main() -> None:
    """
    Основная функция: авторизует все аккаунты из userbot.json последовательно.
    После успешной авторизации отключает клиент — сессия сохранена в файл.
    """
    print("=" * 40)
    print("   Авторизация Telegram-аккаунтов")
    print("=" * 40)

    # Загружаем список аккаунтов
    try:
        data = load_userbot_json()
    except FileNotFoundError as e:
        print(f"❌ {e}")
        return

    users: dict = data.get("users", {})
    if not users:
        print("⚠️  В userbot.json нет ни одного аккаунта.")
        return

    print(f"📋 Найдено аккаунтов: {len(users)}")

    success = 0
    failed  = 0

    for username, user_info in users.items():
        client = await login_user(username, user_info)

        if client is not None:
            # Отключаем после сохранения сессии — бот сам переподключится при старте
            await client.disconnect()
            success += 1
        else:
            failed += 1

    # Итоговый отчёт
    print(f"\n{'=' * 40}")
    print(f"✅ Успешно:  {success}")
    print(f"❌ Ошибки:   {failed}")
    print(f"{'=' * 40}")

    if success > 0:
        print("\n🚀 Теперь можно запускать основной бот: python main.py")


if __name__ == "__main__":
    asyncio.run(main())
