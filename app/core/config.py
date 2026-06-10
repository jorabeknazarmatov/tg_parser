"""
Конфигурация приложения через Pydantic Settings.
Все настройки читаются из переменных окружения или файла .env
"""
from __future__ import annotations

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Главный класс настроек приложения."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== Telegram Bot =====
    # Токен бота, полученный от @BotFather
    BOT_TOKEN: str

    # Список ID администраторов бота
    ADMIN_IDS: list[int] = []

    # ===== Настройки парсера =====
    # За сколько дней назад учитывать активность пользователей
    ACTIVE_DAYS: int = 30

    # ===== Настройки отправки =====
    # Минимальная задержка между отправками в секундах
    SEND_DELAY_MIN: int = 30

    # Максимальная задержка между отправками в секундах
    SEND_DELAY_MAX: int = 90

    # Максимум отправок на один аккаунт за сутки
    MAX_PER_ACCOUNT: int = 40

    # Максимальное число попыток отправки при ошибке
    MAX_RETRIES: int = 3

    # ===== База данных =====
    DB_URL: str = "sqlite+aiosqlite:///data/tg_parser.db"

    # ===== Логирование =====
    LOG_LEVEL: str = "INFO"

    @field_validator("ADMIN_IDS", mode="before")
    @classmethod
    def parse_admin_ids(cls, value: Any) -> list[int]:
        """Парсинг списка admin ID из строки с разделителями-запятыми."""
        if isinstance(value, str):
            return [int(x.strip()) for x in value.split(",") if x.strip()]
        if isinstance(value, list):
            return [int(x) for x in value]
        return []

    @field_validator("SEND_DELAY_MIN")
    @classmethod
    def validate_delay_min(cls, value: int) -> int:
        """Минимальная задержка не может быть отрицательной."""
        if value < 0:
            raise ValueError("SEND_DELAY_MIN должен быть >= 0")
        return value

    @field_validator("SEND_DELAY_MAX")
    @classmethod
    def validate_delay_max(cls, value: int) -> int:
        """Максимальная задержка не может быть меньше 1 секунды."""
        if value < 1:
            raise ValueError("SEND_DELAY_MAX должен быть >= 1")
        return value


# Глобальный экземпляр настроек (singleton)
settings = Settings()
