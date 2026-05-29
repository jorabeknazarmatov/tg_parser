"""
Сервис статистики — собирает агрегированные данные о системе.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger

if TYPE_CHECKING:
    from app.repositories.account_repo import AccountRepository
    from app.repositories.send_log_repo import SendLogRepository
    from app.repositories.task_repo import TaskRepository
    from app.repositories.user_repo import UserRepository

logger = get_logger("bot")


class StatsService:
    """
    Сервис агрегации статистики из всех репозиториев.
    Предоставляет единый интерфейс для получения метрик системы.
    """

    def __init__(
        self,
        user_repo: "UserRepository",
        account_repo: "AccountRepository",
        task_repo: "TaskRepository",
        send_log_repo: "SendLogRepository",
    ) -> None:
        # Репозиторий пользователей
        self._user_repo = user_repo
        # Репозиторий аккаунтов
        self._account_repo = account_repo
        # Репозиторий задач
        self._task_repo = task_repo
        # Репозиторий логов отправки
        self._send_log_repo = send_log_repo

    async def get_full_stats(self) -> dict[str, Any]:
        """
        Собирает полную статистику системы из всех источников.

        Returns:
            Словарь с ключами:
            - total_users, sent_users, failed_users, unsent_users
            - total_accounts, active_accounts, flood_accounts, disabled_accounts
            - total_sent_logs, total_failed_logs, total_flood_logs
            - last_task (dict с данными последней задачи или None)
        """
        # Статистика пользователей
        total_users = await self._user_repo.count_total()
        sent_users = await self._user_repo.count_sent()
        failed_users = await self._user_repo.count_failed()
        unsent_users = await self._user_repo.count_unsent()

        # Статистика аккаунтов
        all_accounts = await self._account_repo.get_all()
        total_accounts = len(all_accounts)
        active_accounts = sum(1 for a in all_accounts if a.status == "active")
        flood_accounts = sum(1 for a in all_accounts if a.status == "flood")
        disabled_accounts = sum(1 for a in all_accounts if a.status == "disabled")

        # Статистика логов
        total_sent_logs = await self._send_log_repo.count_by_status("sent")
        total_failed_logs = await self._send_log_repo.count_by_status("failed")
        total_flood_logs = await self._send_log_repo.count_by_status("flood")

        # Последняя задача
        last_task_obj = await self._task_repo.get_latest()
        last_task = None
        if last_task_obj:
            last_task = {
                "id": last_task_obj.id,
                "type": last_task_obj.type,
                "status": last_task_obj.status,
                "progress": last_task_obj.progress,
                "total": last_task_obj.total,
                "created_at": last_task_obj.created_at,
                "updated_at": last_task_obj.updated_at,
            }

        return {
            "total_users": total_users,
            "sent_users": sent_users,
            "failed_users": failed_users,
            "unsent_users": unsent_users,
            "total_accounts": total_accounts,
            "active_accounts": active_accounts,
            "flood_accounts": flood_accounts,
            "disabled_accounts": disabled_accounts,
            "total_sent_logs": total_sent_logs,
            "total_failed_logs": total_failed_logs,
            "total_flood_logs": total_flood_logs,
            "last_task": last_task,
        }
