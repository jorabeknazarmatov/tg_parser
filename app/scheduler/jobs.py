"""
Фоновые задачи планировщика APScheduler.
Автоматические сбросы счётчиков и проверка FloodWait.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.repositories.account_repo import AccountRepository

logger = get_logger("parser")


async def reset_daily_counts(account_repo: "AccountRepository") -> None:
    """
    Сбрасывает суточные счётчики отправок для всех аккаунтов.
    Запускается каждый день в полночь.

    Args:
        account_repo: Репозиторий аккаунтов
    """
    logger.info("Сброс суточных счётчиков аккаунтов")
    try:
        await account_repo.reset_daily_counts()
        logger.info("Суточные счётчики сброшены")
    except Exception as exc:
        logger.error("Ошибка сброса суточных счётчиков", error=str(exc))


async def check_flood_expired(account_repo: "AccountRepository") -> None:
    """
    Проверяет истёкшие FloodWait и восстанавливает аккаунты.
    Запускается каждые 5 минут.

    Args:
        account_repo: Репозиторий аккаунтов
    """
    try:
        count = await account_repo.check_and_clear_flood()
        if count > 0:
            logger.info("Восстановлены аккаунты после FloodWait", count=count)
    except Exception as exc:
        logger.error("Ошибка проверки FloodWait", error=str(exc))


def setup_scheduler(
    scheduler,
    account_repo: "AccountRepository",
) -> None:
    """
    Регистрирует все фоновые задачи в планировщике APScheduler.

    Args:
        scheduler: Экземпляр AsyncIOScheduler
        account_repo: Репозиторий аккаунтов
    """
    # Сброс суточных счётчиков в полночь каждый день
    scheduler.add_job(
        reset_daily_counts,
        trigger="cron",
        hour=0,
        minute=0,
        second=0,
        kwargs={"account_repo": account_repo},
        id="reset_daily_counts",
        replace_existing=True,
    )

    # Проверка истёкших FloodWait каждые 5 минут
    scheduler.add_job(
        check_flood_expired,
        trigger="interval",
        minutes=5,
        kwargs={"account_repo": account_repo},
        id="check_flood_expired",
        replace_existing=True,
    )

    logger.info("Планировщик задач настроен")
