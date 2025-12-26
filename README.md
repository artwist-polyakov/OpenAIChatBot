# OpenAI ChatBot

Telegram бот с интеграцией OpenAI Responses API.

## Требования

- Python 3.12+
- Docker и Docker Compose (для production)
- OpenAI API ключ
- Telegram Bot Token

## Быстрый старт

### 1. Клонирование и настройка

```bash
git clone <repo-url>
cd OpenAIChatBot

# Копируем конфиг
cp .env.example .env
```

### 2. Настройка .env

```bash
# Telegram
BOT_TOKEN=your_telegram_bot_token

# OpenAI
OPENAI_API_KEY=your_openai_api_key
PROMPT_ID=pmpt_xxx  # ID из Dashboard
```

### 3. Создание Prompt в OpenAI Dashboard

1. Перейдите в [OpenAI Platform](https://platform.openai.com)
2. Создайте новый Prompt с инструкциями и базой знаний
3. Скопируйте PROMPT_ID в `.env`

### 4. Запуск

**Docker (рекомендуется):**
```bash
docker-compose up -d
```

**Локально:**
```bash
cd src
pip install -r requirements.txt
python bot.py
```

## Команды бота

- `/reset` — Сбросить историю диалога
- `/chatinfo` — Информация о текущем чате

## Структура проекта

```
OpenAIChatBot/
├── src/
│   ├── bot.py                    # Точка входа
│   ├── config.py                 # Конфигурация
│   ├── handlers.py               # Обработчики сообщений
│   ├── conversation_manager.py   # Управление conversations
│   ├── access_control.py         # Rate limiting, доступ
│   ├── chat_manager.py           # Персистентность чатов
│   ├── utils.py                  # Утилиты
│   ├── requirements.txt
│   └── Dockerfile
├── data/                         # Данные (chat_list.json)
├── logs/                         # Логи
├── docs/
│   └── MIGRATION_GUIDE.md        # Гайд по миграции
├── docker-compose.yml
├── .env.example
└── README.md
```

## Конфигурация

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Telegram Bot Token | - |
| `OPENAI_API_KEY` | OpenAI API ключ | - |
| `PROMPT_ID` | ID Prompt из Dashboard | - |
| `USERS` | Whitelist usernames или `*` | `*` |
| `ALLOWED_CHATS` | Whitelist chat_id или `*` | `*` |
| `RATE_LIMIT_MESSAGES` | Макс сообщений в окне | `10` |
| `RATE_LIMIT_WINDOW` | Временное окно (сек) | `60` |
| `CONVERSATION_LIFETIME_HOURS` | TTL conversations | `24` |

## Мониторинг (Sentry)

Для включения мониторинга добавьте в `.env`:

```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
SENTRY_ENVIRONMENT=production
```

## Документация

- [Гайд по миграции с Assistants API](docs/MIGRATION_GUIDE.md)
- [OpenAI Responses API](https://platform.openai.com/docs/api-reference/responses)

## Лицензия

MIT
