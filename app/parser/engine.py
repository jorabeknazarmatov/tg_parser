"""
Основной движок парсинга Telegram-чатов и каналов.
Обрабатывает сообщения, извлекает пользователей по ключевым словам.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, AsyncIterator

from app.core.logging import get_logger
from app.parser.keyword_matcher import KeywordMatcher
from app.parser.user_validator import UserValidator

if TYPE_CHECKING:
    from telethon import TelegramClient
    from telethon.types import Message

    from app.core.account_manager import AccountManager
    from app.core.config import Settings
    from app.models.task import Task
    from app.repositories.task_repo import TaskRepository
    from app.repositories.user_repo import UserRepository

logger = get_logger("parser")


class ParserEngine:
    """
    Движок парсинга Telegram-каналов и групп.
    Обходит сообщения, находит активных пользователей по ключевым словам
    и сохраняет их в базу данных.
    """

    def __init__(
        self,
        account_manager: "AccountManager",
        user_repo: "UserRepository",
        task_repo: "TaskRepository",
        settings: "Settings",
    ) -> None:
        # Менеджер Telegram-аккаунтов для парсинга
        self._account_manager = account_manager
        # Репозиторий пользователей
        self._user_repo = user_repo
        # Репозиторий задач
        self._task_repo = task_repo
        # Настройки приложения
        self._settings = settings
        # Флаг остановки задачи
        self._stop_flag = False

    def stop(self) -> None:
        """Устанавливает флаг для остановки парсинга."""
        self._stop_flag = True

    async def parse_all(self, task_id: int) -> None:
        """
        Главная точка входа: парсит все сущности из to_parse.json.
        Обновляет прогресс задачи в базе данных.

        Args:
            task_id: ID задачи для обновления прогресса
        """
        self._stop_flag = False

        try:
            # Загружаем список источников для парсинга
            import json
            import aiofiles

            async with aiofiles.open("data/to_parse.json", encoding="utf-8") as f:
                entities: list[str] = json.loads(await f.read())

            if not entities:
                logger.warning("Список источников для парсинга пуст")
                await self._task_repo.update_status(task_id, "done")
                return

            await self._task_repo.update_progress(task_id, 0, len(entities))
            await self._task_repo.update_status(task_id, "running")

            # Загружаем ключевые слова
            keyword_matcher = await KeywordMatcher.load_from_file("data/keywords.json")
            validator = UserValidator()

            logger.info(
                "Начало парсинга",
                entities_count=len(entities),
                keywords_count=len(keyword_matcher),
            )

            for idx, entity_username in enumerate(entities):
                if self._stop_flag:
                    logger.info("Парсинг остановлен пользователем")
                    await self._task_repo.update_status(task_id, "stopped")
                    return

                # Получаем доступный клиент (без лимита sent_today)
                client_data = await self._account_manager.get_available_client_for_parse()
                if client_data is None:
                    logger.error("Нет доступных аккаунтов для парсинга")
                    await self._task_repo.update_status(task_id, "failed")
                    return

                client, account = client_data

                try:
                    await self.parse_entity(
                        client,
                        entity_username,
                        keyword_matcher,
                        validator,
                        task_id,
                    )
                except Exception as exc:
                    logger.error(
                        "Ошибка при парсинге сущности",
                        entity=entity_username,
                        error=str(exc),
                    )
                finally:
                    self._account_manager.release_client(account.session_name)

                # Обновляем прогресс по количеству обработанных источников
                await self._task_repo.update_progress(task_id, idx + 1, len(entities))

            await self._task_repo.update_status(task_id, "done")
            logger.info("Парсинг завершён", task_id=task_id)

        except Exception as exc:
            logger.error("Критическая ошибка парсинга", error=str(exc))
            await self._task_repo.update_status(task_id, "failed")
            raise

    async def parse_entity(
        self,
        client: "TelegramClient",
        entity_username: str,
        keyword_matcher: KeywordMatcher,
        validator: UserValidator,
        task_id: int,
    ) -> None:
        """
        Парсит одну сущность (канал или группу).
        Обходит сообщения, ищет ключевые слова, добавляет пользователей.

        Args:
            client: Telethon-клиент
            entity_username: Username или ID сущности
            keyword_matcher: Матчер ключевых слов
            validator: Валидатор пользователей
            task_id: ID задачи
        """
        logger.info("Парсинг сущности", entity=entity_username)

        try:
            entity = await client.get_entity(entity_username)
        except Exception as exc:
            logger.error(
                "Не удалось получить сущность",
                entity=entity_username,
                error=str(exc),
            )
            return

        # Получаем администраторов чата
        chat_admins: set[int] = set()
        try:
            async for admin in client.iter_participants(entity, filter="admins"):
                chat_admins.add(admin.id)
        except Exception:
            # Для каналов может не быть прав на получение администраторов
            pass

        # Проверяем, есть ли связанный чат (discussion group)
        entities_to_parse = [entity]
        try:
            from telethon.types import Channel
            if isinstance(entity, Channel) and entity.linked_chat_id:
                linked = await client.get_entity(entity.linked_chat_id)
                entities_to_parse.append(linked)
                logger.info(
                    "Найден связанный чат",
                    entity=entity_username,
                    linked_id=entity.linked_chat_id,
                )
        except Exception:
            pass

        users_batch: list[dict] = []

        for target_entity in entities_to_parse:
            async for message in self.get_messages_since(client, target_entity, self._settings.ACTIVE_DAYS):
                if self._stop_flag:
                    break

                # Проверяем текст сообщения на ключевые слова
                text = message.message or ""
                keyword = keyword_matcher.matches(text)
                if keyword is None:
                    continue

                # Получаем отправителя сообщения
                sender = await message.get_sender()
                if sender is None:
                    continue

                from telethon.types import User as TgUser
                if not isinstance(sender, TgUser):
                    continue

                # Валидируем пользователя
                if not validator.validate(sender, chat_admins):
                    continue

                # Формируем данные для записи
                user_data = self.extract_user_data(
                    sender, message, entity_username, keyword
                )

                users_batch.append(user_data)

                # Сохраняем батчами по 50
                if len(users_batch) >= 50:
                    saved = await self._user_repo.bulk_create(users_batch)
                    logger.info("Сохранено пользователей", count=saved)
                    users_batch.clear()

        # Сохраняем остаток
        if users_batch:
            saved = await self._user_repo.bulk_create(users_batch)
            logger.info("Сохранено пользователей (финал)", count=saved, entity=entity_username)

    async def get_messages_since(
        self,
        client: "TelegramClient",
        entity: object,
        days: int,
    ) -> AsyncIterator["Message"]:
        """
        Асинхронно итерирует сообщения за последние N дней.

        Args:
            client: Telethon-клиент
            entity: Сущность (канал/группа)
            days: Количество дней назад

        Yields:
            Объекты Message
        """
        cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=days)

        async for message in client.iter_messages(entity, limit=None):
            if self._stop_flag:
                return

            # Проверяем дату сообщения
            msg_date = message.date
            if msg_date and msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)

            if msg_date and msg_date < cutoff_date:
                # Сообщения идут в обратном порядке — дальше старее
                return

            yield message

    def extract_user_data(
        self,
        user: object,
        message: "Message",
        entity_name: str,
        keyword: str,
    ) -> dict:
        """
        Извлекает данные пользователя в словарь для сохранения в БД.

        Args:
            user: Объект пользователя Telethon
            message: Сообщение, в котором найдено ключевое слово
            entity_name: Username источника
            keyword: Найденное ключевое слово

        Returns:
            Словарь с данными для создания записи User
        """
        from app.parser.user_validator import UserValidator

        validator = UserValidator()

        # Дата последней активности = дата сообщения
        msg_date = message.date
        if msg_date and msg_date.tzinfo is None:
            msg_date = msg_date.replace(tzinfo=timezone.utc)
        if msg_date is None:
            msg_date = datetime.now(tz=timezone.utc)

        return {
            "telegram_id": user.id,
            "username": getattr(user, "username", None),
            "first_name": getattr(user, "first_name", None),
            "last_name": getattr(user, "last_name", None),
            "phone": getattr(user, "phone", None),
            "source_chat": entity_name,
            "matched_keyword": keyword,
            "last_activity_date": msg_date,
            "unique_hash": validator.make_hash(user.id, entity_name),
        }
