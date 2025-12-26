"""Управление conversations через OpenAI Responses API (previous_response_id)."""
import heapq
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from openai import AsyncOpenAI

from config import OPENAI_API_KEY, CONVERSATION_LIFETIME_HOURS

# OpenAI клиент
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Тип ключа: (chat_id, user_id)
ConversationKey = Tuple[int, int]


@dataclass
class ConversationInfo:
    """Информация о диалоге пользователя."""
    last_response_id: str  # ID последнего ответа для продолжения диалога
    last_access: datetime
    chat_id: int
    user_id: int

    def __lt__(self, other):
        return self.last_access < other.last_access

    @property
    def key(self) -> ConversationKey:
        return (self.chat_id, self.user_id)


# Структуры данных для хранения информации о conversations
conversation_heap = []  # heap для быстрого доступа к старым conversations
chat_user_conversations: Dict[ConversationKey, ConversationInfo] = {}


def get_previous_response_id(chat_id: int, user_id: int) -> Optional[str]:
    """Получает previous_response_id для продолжения диалога."""
    key = (chat_id, user_id)
    conv_info = chat_user_conversations.get(key)
    if conv_info:
        return conv_info.last_response_id
    return None


def update_conversation(chat_id: int, user_id: int, response_id: str):
    """Обновляет информацию о диалоге после получения ответа."""
    current_time = datetime.now()
    key = (chat_id, user_id)

    existing = chat_user_conversations.get(key)
    if existing:
        # Обновляем существующий
        existing.last_response_id = response_id
        existing.last_access = current_time
        heapq.heapify(conversation_heap)
    else:
        # Создаём новый
        conv_info = ConversationInfo(
            last_response_id=response_id,
            last_access=current_time,
            chat_id=chat_id,
            user_id=user_id
        )
        chat_user_conversations[key] = conv_info
        heapq.heappush(conversation_heap, conv_info)


def delete_user_conversation(chat_id: int, user_id: int) -> bool:
    """Удаляет conversation пользователя (сбрасывает историю). Возвращает True если существовал."""
    key = (chat_id, user_id)
    if key in chat_user_conversations:
        del chat_user_conversations[key]
        logging.info(f"Deleted conversation for chat={chat_id}, user={user_id}")
        return True
    return False


async def cleanup_old_conversations():
    """Очистка старых conversations (запускается как фоновая задача)."""
    try:
        current_time = datetime.now()

        while conversation_heap:
            oldest = conversation_heap[0]

            if current_time - oldest.last_access <= timedelta(
                hours=CONVERSATION_LIFETIME_HOURS
            ):
                break

            oldest = heapq.heappop(conversation_heap)
            key = oldest.key
            if key in chat_user_conversations:
                del chat_user_conversations[key]
                logging.info(
                    f"Cleaned up old conversation for chat={oldest.chat_id}, user={oldest.user_id}"
                )

    except Exception as e:
        logging.error(f"Error in cleanup: {e}")


def clear_all_conversations():
    """Очистка локального кэша conversations (при перезапуске)."""
    chat_user_conversations.clear()
    conversation_heap.clear()
    logging.info("Local conversation cache cleared")
