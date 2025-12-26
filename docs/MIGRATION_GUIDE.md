# Гайд по миграции с Assistants API на Responses API

## Обзор

OpenAI объявил о прекращении поддержки Assistants API:
- **Deprecated**: 26 августа 2025
- **Sunset**: 26 августа 2026

Responses API — новый рекомендуемый способ работы с OpenAI моделями.

## Ключевые отличия

### Архитектура

| Assistants API | Responses API |
|----------------|---------------|
| Assistants (создаются через API) | Prompts (создаются в Dashboard) |
| Threads (управление на сервере) | Conversations (аналог threads) |
| Runs + polling | Синхронные ответы |
| `client.beta.threads.*` | `client.responses.*` |

### Сущности

```
Assistants API          →  Responses API
─────────────────────────────────────────
Assistants              →  Prompts
Threads                 →  Conversations
Runs                    →  (не нужны - ответ синхронный)
Run Steps               →  Items
```

## Изменения в коде

### До (Assistants API)

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

# 1. Создаём тред
thread = await client.beta.threads.create()

# 2. Добавляем сообщение
await client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Привет!"
)

# 3. Создаём run
run = await client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id="asst_xxx"
)

# 4. Polling - ждём завершения
while run.status in ["queued", "in_progress"]:
    await asyncio.sleep(2)
    run = await client.beta.threads.runs.retrieve(
        thread_id=thread.id,
        run_id=run.id
    )

# 5. Получаем ответ
messages = await client.beta.threads.messages.list(thread_id=thread.id)
response = messages.data[0].content[0].text.value
```

### После (Responses API)

```python
from openai import AsyncOpenAI

client = AsyncOpenAI()

# 1. Создаём conversation (опционально)
conversation = await client.responses.conversations.create()

# 2. Отправляем запрос и получаем ответ (синхронно!)
response = await client.responses.create(
    prompt="pmpt_xxx",  # Prompt ID из Dashboard
    input=[{"role": "user", "content": "Привет!"}],
    conversation=conversation.id
)

# Ответ готов сразу
print(response.output_text)
```

## Переменные окружения

### До
```bash
ASSISTANT_ID=asst_xxxxx
THREAD_LIFETIME_HOURS=24
```

### После
```bash
PROMPT_ID=pmpt_xxxxx
CONVERSATION_LIFETIME_HOURS=24
```

## Создание Prompt в Dashboard

1. Перейдите в [OpenAI Platform](https://platform.openai.com)
2. Откройте раздел **Prompts** (или **Chats**)
3. Создайте новый Prompt с:
   - Названием
   - Системной инструкцией
   - Моделью (gpt-4o, gpt-4o-mini)
   - Базой знаний (файлы)
4. Скопируйте `PROMPT_ID` (формат: `pmpt_xxx`)

## Миграция существующих ассистентов

Если у вас уже есть Assistant в OpenAI:

1. Откройте [Assistants](https://platform.openai.com/assistants)
2. Скопируйте настройки:
   - Instructions → System prompt в новом Prompt
   - Files → Загрузите в новый Prompt
   - Model → Выберите в настройках Prompt
3. Создайте новый Prompt с этими настройками
4. Обновите `PROMPT_ID` в `.env`

## Преимущества Responses API

1. **Простота** — нет polling, ответ приходит синхронно
2. **Скорость** — меньше API-вызовов
3. **Conversations** — полноценное управление историей
4. **Prompts в Dashboard** — версионирование и редактирование без деплоя

## Ссылки

- [Migrate to the Responses API](https://platform.openai.com/docs/guides/migrate-to-responses)
- [Assistants migration guide](https://platform.openai.com/docs/assistants/migration)
- [Responses API Reference](https://platform.openai.com/docs/api-reference/responses)
- [Conversations API Reference](https://platform.openai.com/docs/api-reference/conversations)
