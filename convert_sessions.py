"""
Конвертер сессий Pyrogram → Telethon.
Читает существующие .session файлы (Pyrogram) и создаёт совместимые
с Telethon без необходимости повторной авторизации (SMS-код не нужен).

Использование:
    python convert_sessions.py
"""
from __future__ import annotations

import os
import sqlite3
import shutil
from pathlib import Path


SESSIONS_DIR = Path("sessions")

# Адреса серверов Telegram по номеру DC
DC_ADDRESSES: dict[int, tuple[str, int]] = {
    1: ("149.154.175.53",  443),
    2: ("149.154.167.51",  443),
    3: ("149.154.175.100", 443),
    4: ("149.154.167.91",  443),
    5: ("91.108.56.130",   443),
}


def detect_format(session_path: Path) -> str:
    """
    Определяет формат .session файла.

    Returns:
        "telethon"  — уже в нужном формате
        "pyrogram"  — формат Pyrogram (7 колонок)
        "unknown"   — нераспознанный формат
        "empty"     — пустая таблица sessions
    """
    try:
        conn = sqlite3.connect(session_path)
        cur = conn.cursor()

        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not cur.fetchone():
            conn.close()
            return "unknown"

        cur.execute("SELECT * FROM sessions LIMIT 1")
        row = cur.fetchone()
        conn.close()

        if row is None:
            return "empty"
        if len(row) == 5:
            return "telethon"
        if len(row) == 7:
            return "pyrogram"
        return "unknown"

    except sqlite3.DatabaseError:
        return "unknown"


def read_pyrogram_session(session_path: Path) -> dict | None:
    """
    Читает данные из Pyrogram .session файла.

    Pyrogram sessions таблица:
        dc_id INTEGER, api_id INTEGER, test_mode INTEGER,
        auth_key BLOB, date INTEGER, user_id INTEGER, is_bot INTEGER

    Returns:
        Словарь с dc_id, auth_key или None при ошибке
    """
    try:
        conn = sqlite3.connect(session_path)
        cur = conn.cursor()
        cur.execute("SELECT dc_id, auth_key FROM sessions LIMIT 1")
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        dc_id, auth_key = row
        return {"dc_id": dc_id, "auth_key": auth_key}

    except Exception as e:
        print(f"  ❌ Ошибка чтения Pyrogram-сессии: {e}")
        return None


def create_telethon_session(session_path: Path, dc_id: int, auth_key: bytes) -> bool:
    """
    Создаёт .session файл в формате Telethon.

    Telethon sessions таблица:
        dc_id INTEGER NOT NULL, server_address TEXT,
        port INTEGER, auth_key BLOB, takeout_id INTEGER

    Args:
        session_path: Путь к новому .session файлу
        dc_id: Номер датацентра Telegram
        auth_key: Ключ авторизации (256 байт)

    Returns:
        True если файл создан успешно
    """
    server_address, port = DC_ADDRESSES.get(dc_id, ("149.154.167.51", 443))

    try:
        conn = sqlite3.connect(session_path)
        cur = conn.cursor()

        # Создаём все таблицы в формате Telethon
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                dc_id     INTEGER NOT NULL,
                server_address TEXT,
                port      INTEGER,
                auth_key  BLOB,
                takeout_id INTEGER
            );

            CREATE TABLE IF NOT EXISTS entities (
                id       INTEGER PRIMARY KEY,
                hash     INTEGER NOT NULL,
                username TEXT,
                phone    TEXT,
                name     TEXT,
                date     INTEGER
            );

            CREATE TABLE IF NOT EXISTS sent_files (
                md5_digest BLOB,
                file_size  INTEGER,
                type       INTEGER,
                id         TEXT,
                hash       INTEGER,
                PRIMARY KEY (md5_digest, file_size, type)
            );

            CREATE TABLE IF NOT EXISTS update_state (
                id   INTEGER PRIMARY KEY,
                pts  INTEGER,
                qts  INTEGER,
                date INTEGER,
                seq  INTEGER
            );

            CREATE TABLE IF NOT EXISTS version (
                version INTEGER
            );
        """)

        # Записываем данные сессии
        cur.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
            (dc_id, server_address, port, auth_key, None),
        )
        cur.execute("INSERT INTO version VALUES (?)", (1,))
        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print(f"  ❌ Ошибка создания Telethon-сессии: {e}")
        return False


def convert_session(session_file: Path) -> bool:
    """
    Конвертирует один .session файл из формата Pyrogram в Telethon.
    Оригинальный файл сохраняется с расширением .session.bak

    Returns:
        True если конвертация прошла успешно
    """
    name = session_file.stem
    fmt = detect_format(session_file)

    print(f"\n  📄 {session_file.name}  →  формат: {fmt}")

    if fmt == "telethon":
        print(f"  ✅ Уже в формате Telethon, пропускаем.")
        return True

    if fmt in ("unknown", "empty"):
        print(f"  ⚠️  Нераспознанный формат, пропускаем.")
        return False

    # Читаем данные из Pyrogram-сессии
    data = read_pyrogram_session(session_file)
    if not data:
        print(f"  ❌ Не удалось прочитать данные сессии.")
        return False

    dc_id    = data["dc_id"]
    auth_key = data["auth_key"]
    print(f"  📡 DC ID: {dc_id},  auth_key: {len(auth_key)} байт")

    # Делаем резервную копию оригинала
    backup_path = session_file.with_suffix(".session.bak")
    shutil.copy2(session_file, backup_path)
    print(f"  💾 Резервная копия: {backup_path.name}")

    # Удаляем старый файл и создаём новый в формате Telethon
    session_file.unlink()
    success = create_telethon_session(session_file, dc_id, auth_key)

    if success:
        print(f"  ✅ Конвертирован успешно!")
    else:
        # Восстанавливаем резервную копию при ошибке
        shutil.copy2(backup_path, session_file)
        print(f"  🔄 Оригинал восстановлен из резервной копии.")

    return success


def main() -> None:
    """Конвертирует все Pyrogram .session файлы в директории sessions/."""
    print("=" * 50)
    print("  Конвертер сессий: Pyrogram → Telethon")
    print("=" * 50)

    if not SESSIONS_DIR.exists():
        print(f"❌ Директория {SESSIONS_DIR} не найдена.")
        return

    session_files = [
        f for f in SESSIONS_DIR.glob("*.session")
        if not f.name.endswith(".bak")
    ]

    if not session_files:
        print(f"⚠️  В директории {SESSIONS_DIR} нет .session файлов.")
        return

    print(f"\n📋 Найдено .session файлов: {len(session_files)}")

    success = 0
    skipped = 0
    failed  = 0

    for session_file in sorted(session_files):
        result = convert_session(session_file)
        fmt = detect_format(session_file)
        if fmt == "telethon" and result:
            if "Уже в формате" in "":  # отслеживаем через detect до конвертации
                skipped += 1
            else:
                success += 1
        elif not result:
            failed += 1

    # Пересчёт: смотрим финальные форматы
    success = skipped = failed = 0
    for session_file in sorted(session_files):
        fmt = detect_format(session_file)
        if fmt == "telethon":
            success += 1
        else:
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"✅ Готово к работе:  {success}")
    print(f"❌ Не конвертировано: {failed}")
    print(f"{'=' * 50}")

    if success > 0:
        print("\n🚀 Запускайте бот: python main.py")
    if failed > 0:
        print("⚠️  Резервные копии сохранены с расширением .session.bak")


if __name__ == "__main__":
    main()
