"""
Конвертер .session файлов для совместимости с текущей версией Telethon.

Проблема: сессии созданы более новой версией Telethon, которая добавила
колонку tmp_auth_key (итого 6 колонок). Текущая версия Telethon ожидает
5 колонок и падает с ошибкой "too many values to unpack (expected 5)".

Решение: пересоздать таблицу sessions без лишней колонки tmp_auth_key.
auth_key сохраняется — повторная авторизация не нужна.

Использование:
    python convert_sessions.py
"""
from __future__ import annotations

import shutil
import sqlite3
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


def get_column_count(session_path: Path) -> int | None:
    """
    Возвращает количество колонок в таблице sessions.
    None если файл нечитаем или таблица отсутствует.
    """
    try:
        conn = sqlite3.connect(session_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        if not cur.fetchone():
            conn.close()
            return None
        cur.execute("SELECT * FROM sessions LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row is None:
            # Таблица пустая — считаем через PRAGMA
            conn = sqlite3.connect(session_path)
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(sessions)")
            cols = cur.fetchall()
            conn.close()
            return len(cols) if cols else None
        return len(row)
    except sqlite3.DatabaseError:
        return None


def read_session_data(session_path: Path) -> dict | None:
    """
    Читает dc_id, server_address, port, auth_key из таблицы sessions.
    Работает с любым количеством колонок (5, 6 и более).
    """
    try:
        conn = sqlite3.connect(session_path)
        cur = conn.cursor()
        cur.execute(
            "SELECT dc_id, server_address, port, auth_key FROM sessions LIMIT 1"
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return None
        dc_id, server_address, port, auth_key = row
        # Если server_address пустой — берём из таблицы DC
        if not server_address:
            server_address, port = DC_ADDRESSES.get(dc_id, ("149.154.167.51", 443))
        return {
            "dc_id": dc_id,
            "server_address": server_address,
            "port": port,
            "auth_key": auth_key,
        }
    except Exception as e:
        print(f"  ❌ Ошибка чтения сессии: {e}")
        return None


def rewrite_session(session_path: Path, data: dict) -> bool:
    """
    Пересоздаёт .session файл в стандартном формате Telethon (5 колонок).
    Все остальные таблицы (entities, update_state и т.д.) копируются из оригинала.
    """
    tmp_path = session_path.with_suffix(".session.tmp")

    try:
        # Открываем оригинал для копирования остальных таблиц
        src_conn = sqlite3.connect(session_path)
        src_cur = src_conn.cursor()

        # Создаём новый файл
        dst_conn = sqlite3.connect(tmp_path)
        dst_cur = dst_conn.cursor()

        # Стандартная схема Telethon (5 колонок)
        dst_cur.executescript("""
            CREATE TABLE sessions (
                dc_id          integer primary key,
                server_address text,
                port           integer,
                auth_key       blob,
                takeout_id     integer
            );
            CREATE TABLE entities (
                id       integer primary key,
                hash     integer not null,
                username text,
                phone    integer,
                name     text,
                date     integer
            );
            CREATE TABLE sent_files (
                md5_digest blob,
                file_size  integer,
                type       integer,
                id         integer,
                hash       integer,
                primary key (md5_digest, file_size, type)
            );
            CREATE TABLE update_state (
                id   integer primary key,
                pts  integer,
                qts  integer,
                date integer,
                seq  integer
            );
            CREATE TABLE version (
                version integer primary key
            );
        """)

        # Записываем сессию (5 колонок, без tmp_auth_key)
        dst_cur.execute(
            "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?)",
            (data["dc_id"], data["server_address"], data["port"], data["auth_key"], None),
        )

        # Копируем entities если есть
        try:
            src_cur.execute("SELECT id, hash, username, phone, name, date FROM entities")
            rows = src_cur.fetchall()
            if rows:
                dst_cur.executemany(
                    "INSERT OR IGNORE INTO entities VALUES (?, ?, ?, ?, ?, ?)", rows
                )
                print(f"  📦 Скопировано entities: {len(rows)}")
        except sqlite3.OperationalError:
            pass

        # Копируем update_state если есть
        try:
            src_cur.execute("SELECT id, pts, qts, date, seq FROM update_state")
            rows = src_cur.fetchall()
            if rows:
                dst_cur.executemany(
                    "INSERT OR IGNORE INTO update_state VALUES (?, ?, ?, ?, ?)", rows
                )
        except sqlite3.OperationalError:
            pass

        dst_cur.execute("INSERT OR IGNORE INTO version VALUES (1)")
        dst_conn.commit()
        dst_conn.close()
        src_conn.close()

        # Заменяем оригинал
        session_path.unlink()
        tmp_path.rename(session_path)
        return True

    except Exception as e:
        print(f"  ❌ Ошибка пересоздания сессии: {e}")
        if tmp_path.exists():
            tmp_path.unlink()
        return False


def convert_session(session_file: Path) -> str:
    """
    Конвертирует один .session файл.

    Returns:
        "ok"      — уже совместима, ничего не делали
        "fixed"   — исправлена успешно
        "failed"  — ошибка
    """
    col_count = get_column_count(session_file)
    print(f"\n  📄 {session_file.name}  →  колонок в sessions: {col_count}")

    if col_count == 5:
        print(f"  ✅ Уже совместима с Telethon, пропускаем.")
        return "ok"

    if col_count is None:
        print(f"  ⚠️  Не удалось прочитать файл.")
        return "failed"

    # Читаем данные авторизации
    data = read_session_data(session_file)
    if not data:
        print(f"  ❌ Данные сессии пусты.")
        return "failed"

    print(f"  📡 DC {data['dc_id']}  {data['server_address']}:{data['port']}")
    print(f"  🔑 auth_key: {len(data['auth_key'])} байт")

    # Резервная копия
    backup = session_file.with_suffix(".session.bak")
    shutil.copy2(session_file, backup)
    print(f"  💾 Резервная копия: {backup.name}")

    success = rewrite_session(session_file, data)
    if success:
        print(f"  ✅ Исправлена! (было {col_count} колонок → стало 5)")
        return "fixed"
    else:
        # Восстанавливаем оригинал
        shutil.copy2(backup, session_file)
        print(f"  🔄 Оригинал восстановлен из резервной копии.")
        return "failed"


def main() -> None:
    """Конвертирует все несовместимые .session файлы в директории sessions/."""
    print("=" * 52)
    print("  Исправление .session файлов для Telethon")
    print("=" * 52)

    if not SESSIONS_DIR.exists():
        print(f"❌ Директория {SESSIONS_DIR} не найдена.")
        return

    session_files = sorted(
        f for f in SESSIONS_DIR.glob("*.session")
        if not f.name.endswith(".bak")
    )

    if not session_files:
        print(f"⚠️  В директории {SESSIONS_DIR} нет .session файлов.")
        return

    print(f"\n📋 Найдено файлов: {len(session_files)}")

    results = {"ok": 0, "fixed": 0, "failed": 0}
    for session_file in session_files:
        result = convert_session(session_file)
        results[result] += 1

    print(f"\n{'=' * 52}")
    print(f"✅ Уже совместимы:  {results['ok']}")
    print(f"🔧 Исправлено:      {results['fixed']}")
    print(f"❌ Ошибки:          {results['failed']}")
    print(f"{'=' * 52}")

    if results["fixed"] + results["ok"] > 0:
        print("\n🚀 Запускайте бот: python main.py")


if __name__ == "__main__":
    main()
