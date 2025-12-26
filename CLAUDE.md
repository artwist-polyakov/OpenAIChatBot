# OpenAI ChatBot - Claude Instructions

## Project Overview

Telegram бот с интеграцией OpenAI Responses API. Использует Conversations для управления историей диалогов.

**Tech Stack:**
- Python 3.12
- python-telegram-bot 21.x (async)
- openai 2.14.0+ (Responses API)
- Sentry для мониторинга
- Docker для deployment

## Architecture

### Слои приложения

```
bot.py                    # Точка входа, инициализация, graceful shutdown
├── handlers.py           # Обработка сообщений и команд
│   ├── conversation_manager.py  # Управление OpenAI Conversations
│   ├── access_control.py        # Rate limiting, whitelist/blacklist
│   └── chat_manager.py          # Персистентность данных о чатах
└── config.py             # Загрузка переменных окружения
```

### Поток обработки сообщения

1. Валидация сообщения (`handlers.py`)
2. Проверка доступа (`access_control.py`)
3. Rate limiting (`access_control.py`)
4. Получение/создание conversation (`conversation_manager.py`)
5. Вызов Responses API (`handlers.py`)
6. Очистка ответа (`utils.py`)
7. Отправка ответа пользователю

### Управление Conversations

- Conversations хранятся в памяти с heap-структурой для TTL
- Ключ: `(chat_id, user_id)` — уникальный для каждого пользователя в каждом чате
- Автоочистка через `CONVERSATION_LIFETIME_HOURS` (по умолчанию 24 часа)
- Фоновая задача `cleanup_old_conversations()` запускается каждый час

## Development Commands

### Docker
```bash
docker-compose up -d        # Запуск
docker-compose logs -f      # Логи
docker-compose down         # Остановка
docker-compose build        # Пересборка
```

### Локальная разработка
```bash
cd src
pip install -r requirements.txt
python bot.py
```

### Проверка синтаксиса
```bash
python -m py_compile src/*.py
```

### Линтинг
```bash
python -m flake8 src/
python -m isort src/ --check-only
```

## Key Files

| Файл | Назначение |
|------|-----------|
| `src/conversation_manager.py` | Работа с OpenAI Conversations API |
| `src/handlers.py` | Обработка сообщений, вызов Responses API |
| `src/access_control.py` | Rate limiting, whitelist/blacklist, file lock |
| `src/config.py` | Загрузка env переменных |
| `src/bot.py` | Точка входа, graceful shutdown |

## OpenAI Integration

### Responses API

```python
response = await client.responses.create(
    prompt=PROMPT_ID,
    input=[{"role": "user", "content": message}],
    conversation=conversation_id
)
```

### Conversations API

```python
# Создание
conversation = await client.responses.conversations.create()

# Удаление
await client.responses.conversations.delete(conversation_id)
```

## Code Style

- Max line length: 99
- Complexity: 10
- Formatter: black, isort
- Linter: flake8

## Important Notes

- Не читать/писать `.env` файлы
- Responses API возвращает ответ синхронно (без polling)
- PROMPT_ID создаётся в OpenAI Dashboard, не через API
- Conversations — аналог Threads из Assistants API
