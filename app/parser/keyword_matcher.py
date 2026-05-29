"""
Сопоставитель ключевых слов для фильтрации сообщений при парсинге.
Поддерживает частичное совпадение и нормализацию текста.
"""
from __future__ import annotations

import unicodedata
from pathlib import Path
from typing import Optional

import aiofiles
import json


class KeywordMatcher:
    """
    Проверяет, содержит ли текст одно из заданных ключевых слов.
    Нормализует текст перед проверкой для устойчивости к регистру и Unicode.
    """

    def __init__(self, keywords: list[str]) -> None:
        # Нормализованный список ключевых слов для поиска
        self._keywords: list[str] = [self.normalize(kw) for kw in keywords if kw.strip()]

    @classmethod
    async def load_from_file(cls, path: str) -> "KeywordMatcher":
        """
        Загружает ключевые слова из JSON-файла.
        Файл должен содержать список строк.

        Args:
            path: Путь к JSON-файлу со списком ключевых слов

        Returns:
            Инициализированный экземпляр KeywordMatcher
        """
        async with aiofiles.open(path, encoding="utf-8") as f:
            content = await f.read()
        keywords: list[str] = json.loads(content)
        return cls(keywords)

    def matches(self, text: str) -> Optional[str]:
        """
        Проверяет, содержит ли текст хотя бы одно ключевое слово.

        Args:
            text: Текст для проверки

        Returns:
            Первое найденное ключевое слово или None
        """
        if not text:
            return None
        normalized = self.normalize(text)
        for keyword in self._keywords:
            if keyword in normalized:
                return keyword
        return None

    def normalize(self, text: str) -> str:
        """
        Нормализует текст для устойчивого сравнения.
        Приводит к нижнему регистру и нормализует Unicode.

        Args:
            text: Исходный текст

        Returns:
            Нормализованный текст
        """
        # Нормализация Unicode: разложение символов
        text = unicodedata.normalize("NFKD", text)
        # Приводим к нижнему регистру
        return text.lower()

    @property
    def keywords(self) -> list[str]:
        """Возвращает список нормализованных ключевых слов."""
        return list(self._keywords)

    def __len__(self) -> int:
        return len(self._keywords)
