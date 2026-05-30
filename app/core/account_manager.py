"""
Менеджер Telegram-аккаунтов для парсинга и рассылки.
Управляет пулом TelegramClient, сессиями и доступностью аккаунтов.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from telethon import TelegramClient

from app.core.logging import get_logger
from app.core.userbot_loader import load_userbot_configs
from app.core.session_checker import is_telethon_session

if TYPE_CHECKING:
    from app.core.config import Settings
    from app.models.account import Account
    from app.repositories.account_repo import AccountRepository

logger = get_logger("parser")


class AccountManager:
    """
    Управляет пулом Telegram-аккаунтов.
    Обеспечивает ротацию аккаунтов и предотвращает одновременное использование.
    """

    def __init__(
        self,
        settings: "Settings",
        account_repo: "AccountRepository",
    ) -> None:
        self._settings = settings
        self._account_repo = account_repo
        # session_name -> TelegramClient
        self._clients: dict[str, TelegramClient] = {}
        # занятые аккаунты (в процессе отправки)
        self._in_use: set[str] = set()
        self._lock = asyncio.Lock()

    async def load_sessions(self) -> int:
        """
        Загружает .session файлы из директории sessions/.
        Для каждого файла ищет api_id/api_hash в userbot.json;
        если не найден — использует глобальные настройки из .env.

        Returns:
            Количество успешно загруженных сессий
        """
        sessions_dir = Path("sessions")
        sessions_dir.mkdir(exist_ok=True)

        # Читаем userbot.json (session_name -> UserbotConfig)
        userbot_configs = load_userbot_configs()

        session_files = list(sessions_dir.glob("*.session"))
        logger.info("Найдено сессий", count=len(session_files))

        loaded = 0
        for session_file in session_files:
            session_name = session_file.stem
            try:
                # Берём api_id/api_hash из userbot.json или из глобальных настроек
                cfg = userbot_configs.get(session_name)
                if cfg:
                    api_id = cfg.api_id
                    api_hash = cfg.api_hash
                    logger.info(
                        "Используются credentials из userbot.json",
                        session=session_name,
                        number=cfg.number,
                    )
                else:
                    api_id = self._settings.API_ID
                    api_hash = self._settings.API_HASH
                    logger.info(
                        "Используются глобальные credentials",
                        session=session_name,
                    )

                # Проверяем совместимость файла сессии с Telethon.
                # Pyrogram и другие библиотеки создают .session с иной схемой БД.
                if not is_telethon_session(str(session_file)):
                    logger.error(
                        "Файл сессии несовместим с Telethon (возможно, создан Pyrogram). "
                        "Удалите файл и выполните re-login: python login_sessions.py",
                        session=session_name,
                        file=str(session_file),
                    )
                    continue

                client = TelegramClient(
                    str(session_file),
                    api_id,
                    api_hash,
                )
                self._clients[session_name] = client

                await self._account_repo.create_or_update(session_name)
                loaded += 1

                logger.info("Сессия загружена", session=session_name)

            except Exception as exc:
                logger.error(
                    "Ошибка загрузки сессии",
                    session=session_name,
                    error=str(exc),
                )

        return loaded

    async def connect_all(self) -> None:
        """Подключает все загруженные клиенты к Telegram."""
        for session_name, client in self._clients.items():
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    logger.warning(
                        "Сессия не авторизована",
                        session=session_name,
                    )
                else:
                    logger.info("Клиент подключён", session=session_name)
            except Exception as exc:
                logger.error(
                    "Ошибка подключения клиента",
                    session=session_name,
                    error=str(exc),
                )

    async def disconnect_all(self) -> None:
        """Отключает все клиенты от Telegram."""
        for session_name, client in self._clients.items():
            try:
                await client.disconnect()
                logger.info("Клиент отключён", session=session_name)
            except Exception as exc:
                logger.warning(
                    "Ошибка отключения клиента",
                    session=session_name,
                    error=str(exc),
                )

    async def get_available_client_for_parse(
        self,
    ) -> Optional[tuple[TelegramClient, "Account"]]:
        """
        Возвращает доступный клиент для парсинга.
        Не проверяет лимит sent_today — парсинг не расходует дневной лимит.
        """
        async with self._lock:
            active_accounts = await self._account_repo.get_active_for_parse()

            if not active_accounts:
                logger.error(
                    "Нет аккаунтов со статусом active в БД (для парсинга)",
                    total_clients=len(self._clients),
                )
                return None

            for account in active_accounts:
                name = account.session_name
                if name not in self._clients:
                    logger.warning("Аккаунт есть в БД, но нет клиента", session=name)
                    continue
                if name in self._in_use:
                    continue

                client = self._clients[name]
                if not client.is_connected():
                    try:
                        await client.connect()
                    except Exception as exc:
                        logger.error("Не удалось переподключить клиент", session=name, error=str(exc))
                        continue

                if not await client.is_user_authorized():
                    logger.warning("Сессия не авторизована", session=name)
                    continue

                self._in_use.add(name)
                return client, account

            logger.error(
                "Все active аккаунты заняты или не авторизованы (парсинг)",
                active_in_db=len(active_accounts),
                in_use=len(self._in_use),
            )
            return None

    async def get_available_client(
        self,
    ) -> Optional[tuple[TelegramClient, "Account"]]:
        """
        Возвращает первый доступный TelegramClient вместе с аккаунтом.
        Помечает аккаунт как занятый до вызова release_client().

        Returns:
            Кортеж (client, account) или None если нет доступных
        """
        async with self._lock:
            active_accounts = await self._account_repo.get_active()

            if not active_accounts:
                logger.error(
                    "Нет аккаунтов со статусом active в БД (для отправки)",
                    total_clients=len(self._clients),
                )
                return None

            for account in active_accounts:
                name = account.session_name
                if name not in self._clients:
                    logger.warning("Аккаунт есть в БД, но нет клиента", session=name)
                    continue
                if name in self._in_use:
                    continue

                client = self._clients[name]

                if not client.is_connected():
                    try:
                        await client.connect()
                    except Exception as exc:
                        logger.error(
                            "Не удалось переподключить клиент",
                            session=name,
                            error=str(exc),
                        )
                        continue

                if not await client.is_user_authorized():
                    logger.warning("Сессия не авторизована", session=name)
                    continue

                self._in_use.add(name)
                return client, account

            logger.error(
                "Все active аккаунты заняты или не авторизованы (отправка)",
                active_in_db=len(active_accounts),
                in_use=len(self._in_use),
            )
            return None

    def release_client(self, session_name: str) -> None:
        """
        Освобождает аккаунт после завершения операции.

        Args:
            session_name: Имя сессии для освобождения
        """
        self._in_use.discard(session_name)

    async def get_all_status(self) -> list[dict]:
        """
        Возвращает статус всех аккаунтов.

        Returns:
            Список словарей с информацией о каждом аккаунте
        """
        accounts = await self._account_repo.get_all()
        result = []

        for account in accounts:
            is_connected = (
                account.session_name in self._clients
                and self._clients[account.session_name].is_connected()
            )
            result.append({
                "session_name": account.session_name,
                "status": account.status,
                "sent_today": account.sent_today,
                "total_sent": account.total_sent,
                "is_connected": is_connected,
                "in_use": account.session_name in self._in_use,
                "flood_until": account.flood_until,
            })

        return result
