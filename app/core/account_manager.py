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
        # Настройки приложения (API_ID, API_HASH)
        self._settings = settings
        # Репозиторий аккаунтов для получения статусов
        self._account_repo = account_repo
        # Словарь активных клиентов: session_name -> TelegramClient
        self._clients: dict[str, TelegramClient] = {}
        # Множество занятых аккаунтов (в процессе использования)
        self._in_use: set[str] = set()
        # Блокировка для потокобезопасного доступа к _in_use
        self._lock = asyncio.Lock()

    async def load_sessions(self) -> int:
        """
        Загружает все .session файлы из директории sessions/.
        Создаёт TelegramClient для каждого файла.

        Returns:
            Количество успешно загруженных сессий
        """
        sessions_dir = Path("sessions")
        sessions_dir.mkdir(exist_ok=True)

        session_files = list(sessions_dir.glob("*.session"))
        logger.info("Найдено сессий", count=len(session_files))

        loaded = 0
        for session_file in session_files:
            session_name = session_file.stem
            try:
                # Создаём клиент (ещё не подключаем)
                client = TelegramClient(
                    str(session_file),
                    self._settings.API_ID,
                    self._settings.API_HASH,
                )
                self._clients[session_name] = client

                # Регистрируем или обновляем запись в базе данных
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
            # Получаем активные аккаунты из базы данных
            active_accounts = await self._account_repo.get_active()

            for account in active_accounts:
                name = account.session_name
                # Проверяем что аккаунт не занят и клиент существует
                if name not in self._in_use and name in self._clients:
                    client = self._clients[name]

                    # Проверяем соединение
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
