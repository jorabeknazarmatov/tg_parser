"""
Настройка профессионального логирования через structlog.
Поддерживает JSON-формат, раздельные файлы логов и интеграцию со стандартным logging.
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, WrappedLogger


# Директория для файлов логов
LOGS_DIR = Path("logs")


def _ensure_logs_dir() -> None:
    """Создаёт директорию для логов, если она не существует."""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)


def _add_app_context(
    logger: WrappedLogger, method: str, event_dict: EventDict
) -> EventDict:
    """Добавляет контекст приложения к каждой записи лога."""
    event_dict["app"] = "tg_parser"
    return event_dict


def _create_file_handler(filename: str, level: int = logging.DEBUG) -> logging.Handler:
    """Создаёт ротирующий файловый обработчик логов."""
    handler = logging.handlers.RotatingFileHandler(
        LOGS_DIR / filename,
        maxBytes=10 * 1024 * 1024,  # 10 МБ
        backupCount=5,
        encoding="utf-8",
    )
    handler.setLevel(level)
    return handler


def setup_logging(log_level: str = "INFO") -> None:
    """
    Инициализирует систему логирования для всего приложения.
    Настраивает structlog с JSON-форматированием и раздельными файлами.
    """
    _ensure_logs_dir()

    # Уровень логирования из конфигурации
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Общий форматтер для JSON-вывода
    json_formatter = logging.Formatter(
        '{"time": "%(asctime)s", "level": "%(levelname)s", '
        '"logger": "%(name)s", "message": %(message)s}'
    )

    # Обработчики для конкретных логгеров
    handlers_map: dict[str, list[str]] = {
        "parser": ["parser.log"],
        "sender": ["sender.log"],
        "bot": ["bot.log"],
        "flood": ["flood.log"],
    }

    # Настраиваем стандартный logging для каждого компонента
    for logger_name, log_files in handlers_map.items():
        std_logger = logging.getLogger(f"tg_parser.{logger_name}")
        std_logger.setLevel(numeric_level)
        for log_file in log_files:
            fh = _create_file_handler(log_file)
            fh.setFormatter(json_formatter)
            std_logger.addHandler(fh)

    # Корневой логгер — консоль
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root_logger.addHandler(console_handler)

    # Глобальный файловый обработчик для всех компонентов
    all_handler = _create_file_handler("app.log")
    all_handler.setFormatter(json_formatter)
    root_logger.addHandler(all_handler)

    # Настройка structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            _add_app_context,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Подавляем лишние логи от сторонних библиотек
    logging.getLogger("telethon").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)


def get_logger(name: str) -> Any:
    """
    Возвращает настроенный structlog-логгер с заданным именем.

    Args:
        name: Имя логгера (например 'parser', 'sender', 'bot')

    Returns:
        Экземпляр structlog логгера
    """
    return structlog.get_logger(f"tg_parser.{name}")
