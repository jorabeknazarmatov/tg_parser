"""
Утилита для проверки совместимости .session файлов с Telethon.
Telethon хранит сессию в SQLite с таблицей sessions из 5 колонок.
Pyrogram и другие библиотеки используют иную структуру.
"""
from __future__ import annotations

import sqlite3


def is_telethon_session(session_path: str) -> bool:
    """
    Проверяет совместимость .session файла с Telethon.

    Telethon ожидает таблицу sessions с 5 колонками:
        dc_id, server_address, port, auth_key, takeout_id

    Возвращает True если файл совместим или не существует.
    Возвращает False если файл создан другой библиотекой (Pyrogram и т.д.)
    """
    full_path = session_path if session_path.endswith(".session") else session_path + ".session"

    try:
        import os
        if not os.path.exists(full_path):
            return True  # Файла нет — Telethon создаст новый корректный

        conn = sqlite3.connect(full_path)
        cursor = conn.cursor()

        # Проверяем наличие таблицы sessions
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
        )
        if not cursor.fetchone():
            conn.close()
            return False  # Таблицы sessions нет — несовместимый формат

        # Проверяем количество колонок
        cursor.execute("SELECT * FROM sessions LIMIT 1")
        row = cursor.fetchone()
        conn.close()

        if row is None:
            return True  # Таблица пустая — Telethon запишет сам

        return len(row) == 5  # Telethon ожидает ровно 5 колонок

    except sqlite3.DatabaseError:
        # Повреждённый или не-SQLite файл
        return False
