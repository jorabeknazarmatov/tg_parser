# Telegram Parser + Mass DM

> Система парсинга участников Telegram-каналов/групп и массовой рассылки сообщений.

---

## 🇷🇺 Описание (Русский)

**Telegram Parser + Mass DM** — профессиональная система для:
- Парсинга активных участников Telegram-каналов и групп по ключевым словам
- Хранения собранных пользователей в базе данных SQLite
- Массовой рассылки сообщений с ротацией аккаунтов и защитой от FloodWait
- Управления всем через Telegram-бота с удобным интерфейсом

### Возможности
- ✅ Поддержка множества Telegram-аккаунтов (сессий)
- ✅ Фильтрация по ключевым словам
- ✅ Обход discussion groups (связанные чаты каналов)
- ✅ Защита от дублей через уникальный хэш
- ✅ Автоматическое восстановление после FloodWait
- ✅ Ротация аккаунтов при рассылке
- ✅ JSON-логирование в раздельные файлы
- ✅ Graceful shutdown
- ✅ Docker-поддержка

---

## 📋 Требования

- Python 3.12+
- Telegram Bot Token ([@BotFather](https://t.me/BotFather))
- Telegram API credentials ([my.telegram.org](https://my.telegram.org))
- Один или несколько `.session` файлов (аккаунты для парсинга/рассылки)

---

## 🚀 Установка и запуск

### 1. Клонирование и настройка

```bash
git clone <repo_url>
cd tg_parser

# Создаём виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# или
.venv\Scripts\activate     # Windows

# Устанавливаем зависимости
pip install -r requirements.txt
```

### 2. Конфигурация

```bash
cp .env.example .env
nano .env  # Заполните все параметры
```

### 3. Добавление сессий

Поместите `.session` файлы в директорию `sessions/`:
```bash
mkdir -p sessions
cp your_account.session sessions/
chmod 700 sessions/
chmod 600 sessions/*.session
```

### 4. Настройка источников и ключевых слов

```bash
# Список каналов/групп для парсинга
nano data/to_parse.json
# Пример: ["username1", "username2", "t.me/channel"]

# Ключевые слова для фильтрации
nano data/keywords.json
# Пример: ["крипто", "заработок", "инвестиции"]

# Текст рассылки
nano data/message.txt

# Медиафайл (опционально)
cp photo.jpg media/
```

### 5. Запуск

```bash
python main.py
```

---

## ⚙️ Конфигурация (.env)

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram-бота | — |
| `ADMIN_IDS` | ID администраторов (через запятую) | — |
| `API_ID` | Telegram API ID | — |
| `API_HASH` | Telegram API Hash | — |
| `ACTIVE_DAYS` | Дней активности для парсинга | `30` |
| `SEND_DELAY_MIN` | Мин. задержка между отправками (сек) | `30` |
| `SEND_DELAY_MAX` | Макс. задержка между отправками (сек) | `90` |
| `MAX_PER_ACCOUNT` | Макс. отправок с аккаунта в день | `40` |
| `MAX_RETRIES` | Макс. попыток при ошибке | `3` |
| `DB_URL` | URL базы данных | `sqlite+aiosqlite:///data/tg_parser.db` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |

---

## 🤖 Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Главное меню |
| `/help` | Справка по командам |
| `/find` | Запустить парсинг |
| `/status` | Статус текущей задачи |
| `/stop` | Остановить задачу |
| `/stats` | Статистика системы |
| `/accounts` | Список аккаунтов |
| `/send_test` | Тестовая отправка |

---

## 📁 Структура проекта

```
tg_parser/
├── app/
│   ├── core/           # Конфигурация, логирование, менеджер аккаунтов
│   ├── db/             # Движок и сессии БД
│   ├── models/         # SQLAlchemy модели
│   ├── repositories/   # Слой доступа к данным
│   ├── parser/         # Движок парсинга
│   ├── sender/         # Движок рассылки
│   ├── services/       # Сервисный слой
│   ├── handlers/       # Обработчики команд бота
│   ├── bot/            # Настройка бота
│   ├── filters/        # Фильтры aiogram
│   ├── keyboards/      # Клавиатуры
│   ├── middlewares/    # Middleware
│   ├── scheduler/      # Планировщик задач
│   ├── security/       # Безопасность сессий
│   └── utils/          # Утилиты
├── alembic/            # Миграции БД
├── data/               # Конфиги и данные
├── sessions/           # .session файлы (не в git!)
├── logs/               # Файлы логов
├── media/              # Медиафайлы для рассылки
├── main.py             # Точка входа
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 🐳 Docker

```bash
# Сборка и запуск
cp .env.example .env
# Заполните .env

docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

---

## 🔒 Безопасность

- Директория `sessions/` должна иметь права `700`
- Файлы `.session` должны иметь права `600`
- Файл `.env` не должен попасть в git
- Используйте отдельные аккаунты для рассылки (не основной)
- Соблюдайте лимиты Telegram (MAX_PER_ACCOUNT ≤ 40)

---

---

## 🇺🇿 Ta'rif (O'zbek)

**Telegram Parser + Mass DM** — kanallar va guruhlardan foydalanuvchilarni yig'ish va xabar yuborish tizimi.

### Xususiyatlar
- ✅ Ko'p akkauntlarni qo'llab-quvvatlash
- ✅ Kalit so'zlar bo'yicha filtrlash
- ✅ FloodWait dan avtomatik himoya
- ✅ Telegram-bot orqali boshqarish

### O'rnatish

```bash
# Talablar: Python 3.12+, Telegram Bot Token, API credentials

git clone <repo_url>
cd tg_parser
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# .env faylini to'ldiring

# Session fayllarini sessions/ papkasiga qo'ying
mkdir sessions
cp your_session.session sessions/

python main.py
```

### Bot buyruqlari

| Buyruq | Tavsif |
|--------|--------|
| `/start` | Asosiy menyu |
| `/find` | Parsing boshlash |
| `/status` | Joriy vazifa holati |
| `/stop` | Vazifani to'xtatish |
| `/stats` | Statistika |
| `/accounts` | Akkauntlar ro'yxati |
| `/send_test` | Test xabar yuborish |

---

## 📊 Логи

Логи сохраняются в директории `logs/`:
- `app.log` — все сообщения
- `parser.log` — логи парсинга
- `sender.log` — логи рассылки
- `bot.log` — логи бота
- `flood.log` — события FloodWait

---

## ⚠️ Важно

Данная система предназначена для легитимного использования. Соблюдайте:
- [Правила использования Telegram](https://telegram.org/tos)
- Законодательство о защите персональных данных вашей страны
- Ограничения на массовые рассылки (spam)
