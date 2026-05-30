"""
Главная точка входа приложения Telegram Parser + Mass DM.
Инициализирует все компоненты и запускает бот.
"""
from __future__ import annotations

import asyncio
import signal
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.logging import get_logger, setup_logging

# Инициализируем логирование первым делом
setup_logging(settings.LOG_LEVEL)
logger = get_logger("bot")


async def main() -> None:
    """
    Основная функция запуска приложения.
    Последовательно инициализирует все компоненты.
    """
    logger.info("Запуск Telegram Parser + Mass DM", log_level=settings.LOG_LEVEL)

    # ===== 1. Инициализация базы данных =====
    from app.db.session import init_db
    await init_db(settings.DB_URL)
    logger.info("База данных инициализирована")

    # ===== 2. Проверка безопасности сессий =====
    from app.security.session_guard import SessionGuard
    guard = SessionGuard()
    guard.check_sessions_dir()
    guard.warn_if_insecure()

    # ===== 3. Создание репозиториев =====
    # Создаём фабрику сессий для репозиториев
    from app.db.session import get_session_factory
    session_factory = get_session_factory()

    async with session_factory() as db_session:
        from app.repositories.account_repo import AccountRepository
        from app.repositories.send_log_repo import SendLogRepository
        from app.repositories.task_repo import TaskRepository
        from app.repositories.user_repo import UserRepository

        account_repo = AccountRepository(db_session, settings.MAX_PER_ACCOUNT)
        user_repo = UserRepository(db_session)
        task_repo = TaskRepository(db_session)
        send_log_repo = SendLogRepository(db_session)

        # ===== 4. Инициализация менеджера аккаунтов =====
        from app.core.account_manager import AccountManager
        account_manager = AccountManager(settings, account_repo)
        loaded = await account_manager.load_sessions()
        logger.info("Сессии загружены", count=loaded)

        await account_manager.connect_all()
        logger.info("Аккаунты подключены к Telegram")

        # ===== 5. Создание движков =====
        from app.parser.engine import ParserEngine
        from app.sender.engine import SenderEngine

        parser_engine = ParserEngine(account_manager, user_repo, task_repo, settings)
        sender_engine = SenderEngine(
            account_manager, user_repo, task_repo, send_log_repo, account_repo, settings
        )

        # ===== 6. Создание сервисов =====
        from app.services.parser_service import ParserService
        from app.services.sender_service import SenderService
        from app.services.stats_service import StatsService

        parser_service = ParserService(parser_engine, task_repo, user_repo)
        sender_service = SenderService(sender_engine, task_repo, user_repo)
        stats_service = StatsService(user_repo, account_repo, task_repo, send_log_repo)

        # ===== 7. Настройка планировщика =====
        scheduler = AsyncIOScheduler(timezone="UTC")
        from app.scheduler.jobs import setup_scheduler
        setup_scheduler(scheduler, account_repo)
        scheduler.start()
        logger.info("Планировщик запущен")

        # ===== 8. Создание и настройка бота =====
        bot = Bot(
            token=settings.BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        dp = Dispatcher()

        # Регистрируем обработчики
        from app.bot.router import register_all_handlers
        register_all_handlers(dp)

        # Настраиваем middleware и DI
        from app.bot.middlewares import setup_middlewares
        setup_middlewares(
            dp,
            settings=settings,
            account_manager=account_manager,
            parser_service=parser_service,
            sender_service=sender_service,
            stats_service=stats_service,
            task_repo=task_repo,
            user_repo=user_repo,
        )

        logger.info("Бот настроен, запускаю polling...")

        # ===== 9. Запуск бота с graceful shutdown =====
        try:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
            )
        finally:
            # Graceful shutdown
            logger.info("Остановка сервисов...")
            scheduler.shutdown(wait=False)
            await parser_service.stop_parse_task()
            await sender_service.stop_send_task()
            await account_manager.disconnect_all()
            await bot.session.close()
            logger.info("Приложение завершено")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Приложение остановлено пользователем")
