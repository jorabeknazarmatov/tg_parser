"""
Защита сессий Telegram — проверка прав доступа к файлам сессий.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger("parser")


class SessionGuard:
    """
    Проверяет и обеспечивает безопасность файлов Telegram-сессий.
    Предотвращает доступ к .session файлам третьими лицами.
    """

    def __init__(self, sessions_dir: str = "sessions") -> None:
        # Путь к директории с сессиями
        self._sessions_dir = Path(sessions_dir)

    def check_sessions_dir(self) -> None:
        """
        Проверяет и устанавливает корректные права доступа (700) на директорию.
        Права 700 — только владелец имеет полный доступ.
        """
        if not self._sessions_dir.exists():
            self._sessions_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            logger.info(
                "Директория сессий создана с правами 700",
                path=str(self._sessions_dir),
            )
            return

        # Проверяем права доступа к директории
        dir_stat = self._sessions_dir.stat()
        current_mode = stat.S_IMODE(dir_stat.st_mode)

        if current_mode != 0o700:
            try:
                os.chmod(self._sessions_dir, 0o700)
                logger.info(
                    "Права директории сессий исправлены",
                    path=str(self._sessions_dir),
                    old_mode=oct(current_mode),
                    new_mode="0700",
                )
            except PermissionError as exc:
                logger.warning(
                    "Не удалось изменить права директории сессий",
                    path=str(self._sessions_dir),
                    error=str(exc),
                )

        # Проверяем права на каждый .session файл
        for session_file in self._sessions_dir.glob("*.session"):
            file_stat = session_file.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)
            if file_mode != 0o600:
                try:
                    os.chmod(session_file, 0o600)
                    logger.info(
                        "Права файла сессии исправлены",
                        file=session_file.name,
                    )
                except PermissionError:
                    pass

    def warn_if_insecure(self) -> None:
        """
        Проверяет безопасность и выводит предупреждения.
        Не изменяет права — только информирует.
        """
        if not self._sessions_dir.exists():
            return

        dir_stat = self._sessions_dir.stat()
        current_mode = stat.S_IMODE(dir_stat.st_mode)

        if current_mode & 0o077:
            logger.warning(
                "ВНИМАНИЕ: Директория сессий имеет небезопасные права доступа!",
                path=str(self._sessions_dir),
                current_mode=oct(current_mode),
                recommended="0700",
            )

        for session_file in self._sessions_dir.glob("*.session"):
            file_stat = session_file.stat()
            file_mode = stat.S_IMODE(file_stat.st_mode)
            if file_mode & 0o077:
                logger.warning(
                    "ВНИМАНИЕ: Файл сессии имеет небезопасные права доступа!",
                    file=session_file.name,
                    current_mode=oct(file_mode),
                    recommended="0600",
                )
