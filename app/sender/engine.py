"""
Движок массовой рассылки сообщений через Telegram.
Управляет ротацией аккаунтов, FloodWait и повторными попытками.
"""
from __future__ import annotations

import asyncio
import random
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from app.core.logging import get_logger
from app.sender.queue import SendQueue

if TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.errors import FloodWaitError

    from app.core.account_manager import AccountManager
    from app.core.config import Settings
    from app.models.account import Account
    from app.models.user import User
    from app.repositories.account_repo import AccountRepository
    from app.repositories.send_log_repo import SendLogRepository
    from app.repositories.task_repo import TaskRepository
    from app.repositories.user_repo import UserRepository

logger = get_logger("sender")


class SenderEngine:
    """
    Движок рассылки сообщений.
    Использует паттерн воркеров с семафором для контроля параллелизма.
    """

    def __init__(
        self,
        account_manager: "AccountManager",
        user_repo: "UserRepository",
        task_repo: "TaskRepository",
        send_log_repo: "SendLogRepository",
        account_repo: "AccountRepository",
        settings: "Settings",
    ) -> None:
        # Менеджер Telegram-аккаунтов
        self._account_manager = account_manager
        # Репозиторий пользователей
        self._user_repo = user_repo
        # Репозиторий задач
        self._task_repo = task_repo
        # Репозиторий логов отправки
        self._send_log_repo = send_log_repo
        # Репозиторий аккаунтов
        self._account_repo = account_repo
        # Настройки приложения
        self._settings = settings
        # Флаг остановки
        self._stop_flag = False
        # Семафор для ограничения параллельных отправок
        self._semaphore = asyncio.Semaphore(3)

    def stop(self) -> None:
        """Устанавливает флаг остановки рассылки."""
        self._stop_flag = True

    async def load_message(self) -> tuple[str, Optional[str]]:
        """
        Загружает текст сообщения и опциональный путь к медиафайлу.

        Returns:
            Кортеж (текст сообщения, путь к медиафайлу или None)
        """
        import aiofiles

        # Загружаем текст сообщения
        message_path = Path("data/message.txt")
        if not message_path.exists():
            raise FileNotFoundError("Файл data/message.txt не найден")

        async with aiofiles.open(message_path, encoding="utf-8") as f:
            text = await f.read()

        # Ищем медиафайл в директории media/
        media_path: Optional[str] = None
        media_dir = Path("media")
        if media_dir.exists():
            # Поддерживаем основные форматы изображений и видео
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.mp4", "*.gif"):
                files = list(media_dir.glob(ext))
                if files:
                    media_path = str(files[0])
                    break

        return text.strip(), media_path

    async def send_all(self, task_id: int) -> None:
        """
        Главная точка входа: отправляет сообщения всем несохранённым пользователям.

        Args:
            task_id: ID задачи для обновления прогресса
        """
        self._stop_flag = False

        try:
            # Загружаем сообщение
            text, media_path = await self.load_message()
            logger.info(
                "Сообщение загружено",
                has_media=media_path is not None,
                text_preview=text[:50],
            )

            # Получаем количество пользователей для отправки
            total = await self._user_repo.count_unsent()
            if total == 0:
                logger.info("Нет пользователей для отправки")
                await self._task_repo.update_status(task_id, "done")
                return

            await self._task_repo.update_progress(task_id, 0, total)
            await self._task_repo.update_status(task_id, "running")

            # Заполняем очередь порциями
            queue = SendQueue(maxsize=200)
            sent_count = 0

            while not self._stop_flag:
                # Загружаем следующую порцию пользователей
                users = await self._user_repo.get_unsent(limit=100)
                if not users:
                    break

                # Запускаем воркеры
                tasks = [
                    asyncio.create_task(
                        self._worker(user, text, media_path, task_id)
                    )
                    for user in users
                ]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, bool) and result:
                        sent_count += 1

                await self._task_repo.update_progress(task_id, sent_count, total)

                # Небольшая пауза между порциями
                await asyncio.sleep(1)

            status = "stopped" if self._stop_flag else "done"
            await self._task_repo.update_status(task_id, status)
            logger.info("Рассылка завершена", sent=sent_count, task_id=task_id)

        except Exception as exc:
            logger.error("Критическая ошибка рассылки", error=str(exc))
            await self._task_repo.update_status(task_id, "failed")
            raise

    async def _worker(
        self,
        user: "User",
        text: str,
        media_path: Optional[str],
        task_id: int,
    ) -> bool:
        """
        Воркер для отправки сообщения одному пользователю.
        Использует семафор для ограничения параллелизма.

        Args:
            user: Пользователь-получатель
            text: Текст сообщения
            media_path: Путь к медиафайлу (опционально)
            task_id: ID задачи

        Returns:
            True если сообщение отправлено успешно
        """
        async with self._semaphore:
            if self._stop_flag:
                return False

            for attempt in range(self._settings.MAX_RETRIES):
                if self._stop_flag:
                    return False

                # Получаем доступный аккаунт
                client_data = await self._account_manager.get_available_client()
                if client_data is None:
                    logger.warning("Нет доступных аккаунтов, ожидание...")
                    await asyncio.sleep(60)
                    continue

                client, account = client_data

                try:
                    success = await self.send_to_user(client, account, user, text, media_path)
                    if success:
                        await self._user_repo.mark_sent(user.id)
                        await self._send_log_repo.create(user.id, account.id, "sent")
                        await self._account_repo.increment_sent(account.id)
                        return True
                    else:
                        # Ошибка не FloodWait — повторяем с задержкой
                        delay = (2 ** attempt) * 5
                        await asyncio.sleep(delay)

                except Exception as exc:
                    error_str = str(exc)

                    # Обработка FloodWait
                    if "FloodWait" in error_str or "flood" in error_str.lower():
                        await self.handle_flood_wait(exc, account)
                        await self._send_log_repo.create(user.id, account.id, "flood", error_str)
                        # Не считаем как попытку
                        continue

                    # Обработка PeerFlood
                    if "PeerFlood" in error_str:
                        await self.handle_peer_flood(account)
                        await self._send_log_repo.create(user.id, account.id, "flood", error_str)
                        continue

                    logger.warning(
                        "Ошибка отправки",
                        user_id=user.telegram_id,
                        attempt=attempt + 1,
                        error=error_str,
                    )
                    await self._send_log_repo.create(user.id, account.id, "failed", error_str)

                    # Экспоненциальная задержка между попытками
                    if attempt < self._settings.MAX_RETRIES - 1:
                        await asyncio.sleep(2 ** (attempt + 1))

                finally:
                    self._account_manager.release_client(account.session_name)

            # Превышено количество попыток
            await self._user_repo.mark_failed(user.id, "Превышено количество попыток")
            return False

    async def send_to_user(
        self,
        client: "TelegramClient",
        account: "Account",
        user: "User",
        text: str,
        media_path: Optional[str],
    ) -> bool:
        """
        Непосредственная отправка сообщения пользователю.

        Args:
            client: Telethon-клиент
            account: Аккаунт отправителя
            user: Пользователь-получатель
            text: Текст сообщения
            media_path: Путь к медиафайлу или None

        Returns:
            True при успешной отправке
        """
        try:
            # Случайная задержка перед отправкой
            delay = random.randint(
                self._settings.SEND_DELAY_MIN,
                self._settings.SEND_DELAY_MAX,
            )
            await asyncio.sleep(delay)

            # Определяем получателя: username или telegram_id
            recipient = user.username if user.username else user.telegram_id

            if media_path:
                await client.send_file(
                    recipient,
                    file=media_path,
                    caption=text,
                )
            else:
                await client.send_message(recipient, text)

            logger.info(
                "Сообщение отправлено",
                user_id=user.telegram_id,
                account=account.session_name,
            )
            return True

        except Exception as exc:
            # Пробрасываем исключение для обработки выше
            raise exc

    async def handle_flood_wait(
        self, exception: Exception, account: "Account"
    ) -> None:
        """
        Обрабатывает FloodWait — устанавливает блокировку аккаунта.

        Args:
            exception: Объект исключения FloodWaitError
            account: Аккаунт, получивший FloodWait
        """
        # Пытаемся извлечь время ожидания из исключения
        seconds = getattr(exception, "seconds", 300)
        if seconds < 60:
            seconds = 60  # Минимум 1 минута

        logger.warning(
            "FloodWait получен",
            account=account.session_name,
            seconds=seconds,
        )

        # Устанавливаем FloodWait в репозитории
        from app.db.session import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            from app.repositories.account_repo import AccountRepository
            repo = AccountRepository(session, self._settings.MAX_PER_ACCOUNT)
            await repo.set_flood(account.id, seconds)
            await session.commit()

    async def handle_peer_flood(self, account: "Account") -> None:
        """
        Обрабатывает PeerFloodError — отключает аккаунт.

        Args:
            account: Аккаунт, получивший PeerFlood
        """
        logger.error(
            "PeerFlood — аккаунт отключён",
            account=account.session_name,
        )

        from app.db.session import get_session_factory
        factory = get_session_factory()
        async with factory() as session:
            from app.repositories.account_repo import AccountRepository
            repo = AccountRepository(session, self._settings.MAX_PER_ACCOUNT)
            await repo.set_disabled(account.id)
            await session.commit()
