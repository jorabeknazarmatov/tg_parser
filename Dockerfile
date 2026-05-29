# ============================================================
# Многоэтапная сборка Docker для Telegram Parser + Mass DM
# Базовый образ: Python 3.12 slim
# ============================================================

# ===== Этап 1: Сборка зависимостей =====
FROM python:3.12-slim AS builder

# Устанавливаем системные зависимости для сборки
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Создаём виртуальное окружение
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Копируем и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===== Этап 2: Финальный образ =====
FROM python:3.12-slim AS final

# Метаданные образа
LABEL maintainer="tg_parser"
LABEL description="Telegram Parser + Mass DM System"

# Системные зависимости только для запуска
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    && rm -rf /var/lib/apt/lists/*

# Создаём непривилегированного пользователя
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копируем виртуальное окружение из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Рабочая директория
WORKDIR /app

# Копируем исходный код
COPY --chown=appuser:appuser . .

# Создаём необходимые директории с правильными правами
RUN mkdir -p sessions data logs media alembic/versions && \
    chmod 700 sessions && \
    chown -R appuser:appuser /app

# Переключаемся на непривилегированного пользователя
USER appuser

# Переменные окружения
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Порт не нужен (бот использует polling)
# EXPOSE 8080

# Проверка работоспособности
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import app.core.config; print('OK')" || exit 1

# Запуск приложения
CMD ["python", "main.py"]
