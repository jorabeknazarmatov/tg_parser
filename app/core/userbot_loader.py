"""
Загрузчик конфигурации аккаунтов из userbot.json.
Формат файла:
{
    "users": {
        "1": {
            "number": "+998901234567",
            "api_id": "12345678",
            "api_hash": "abcdef...",
            "session": "user_1"
        },
        ...
    }
}
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger("parser")

USERBOT_JSON_PATH = Path("sessions/userbot.json")


@dataclass
class UserbotConfig:
    """Конфигурация одного аккаунта из userbot.json."""
    number: str
    api_id: int
    api_hash: str
    session: str  # имя сессии без .session


def load_userbot_configs(path: Path = USERBOT_JSON_PATH) -> dict[str, UserbotConfig]:
    """
    Читает userbot.json и возвращает словарь session_name -> UserbotConfig.
    Если файл не найден — возвращает пустой словарь (fallback на глобальные настройки).
    """
    if not path.exists():
        logger.warning("userbot.json не найден, используются глобальные API_ID/API_HASH", path=str(path))
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.error("Ошибка чтения userbot.json", error=str(exc))
        return {}

    configs: dict[str, UserbotConfig] = {}
    for uid, info in data.get("users", {}).items():
        try:
            cfg = UserbotConfig(
                number=info["number"],
                api_id=int(info["api_id"]),
                api_hash=info["api_hash"],
                session=info["session"],
            )
            configs[cfg.session] = cfg
            logger.info("Конфиг аккаунта загружен", session=cfg.session, number=cfg.number)
        except (KeyError, ValueError) as exc:
            logger.warning("Пропуск записи userbot.json", uid=uid, error=str(exc))

    return configs
