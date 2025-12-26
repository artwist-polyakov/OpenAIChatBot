"""Обработчики команд и сообщений Telegram."""
import logging
import re

import sentry_sdk
from telegram import Update
from telegram.constants import ChatAction
from telegram.error import BadRequest, Forbidden, NetworkError
from telegram.ext import ContextTypes
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from access_control import check_rate_limit, should_bot_respond
from chat_manager import ChatManager
from citations import ProcessedResponse, process_response_with_citations
from config import MAX_MESSAGE_LENGTH, PROMPT_ID, RATE_LIMIT_WINDOW, USERS
from conversation_manager import (
    client,
    get_previous_response_id,
    update_conversation,
    delete_user_conversation,
)

# Менеджер чатов
chat_manager = ChatManager()


@retry(
    retry=retry_if_exception_type(NetworkError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
)
async def send_reply_with_retry(message, text: str, parse_mode: str = None):
    """Отправка ответа с retry при сетевых ошибках."""
    await message.reply_text(text, parse_mode=parse_mode)


TELEGRAM_MESSAGE_LIMIT = 4096


def split_message(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    """Разбивает длинное сообщение на части."""
    if len(text) <= limit:
        return [text]

    parts = []
    while text:
        if len(text) <= limit:
            parts.append(text)
            break

        # Ищем место для разбивки (по переносу строки или пробелу)
        split_pos = text.rfind('\n', 0, limit)
        if split_pos == -1 or split_pos < limit // 2:
            split_pos = text.rfind(' ', 0, limit)
        if split_pos == -1 or split_pos < limit // 2:
            split_pos = limit

        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return parts


async def send_formatted_reply(message, processed: ProcessedResponse):
    """Отправляет форматированный ответ с citations (plain text)."""
    # Убираем MarkdownV2 форматирование - отправляем plain text
    full_text = remove_markdown_formatting(processed.text)

    if processed.footnotes:
        full_text += remove_markdown_formatting(processed.footnotes)

    # Разбиваем на части если слишком длинное
    parts = split_message(full_text)

    for part in parts:
        await send_reply_with_retry(message, part)


def remove_markdown_formatting(text: str) -> str:
    """Удаляет форматирование MarkdownV2 из текста."""
    # Убираем escape-символы
    result = re.sub(r'\\([_*\[\]()~`>#+=|{}.!-])', r'\1', text)
    # Убираем курсив и жирный
    result = re.sub(r'_([^_]+)_', r'\1', result)
    result = re.sub(r'\*([^*]+)\*', r'\1', result)
    return result


async def process_with_responses(chat_id: int, user_id: int, message_text: str):
    """Отправляет сообщение через Responses API и возвращает response объект."""
    # Получаем previous_response_id для продолжения диалога
    previous_response_id = get_previous_response_id(chat_id, user_id)

    # Формируем параметры запроса
    params = {
        "prompt": {"id": PROMPT_ID},
        "input": [{"role": "user", "content": message_text}],
    }

    # Добавляем previous_response_id если есть история
    if previous_response_id:
        params["previous_response_id"] = previous_response_id

    # Выполняем запрос к Responses API
    response = await client.responses.create(**params)

    # Сохраняем response.id для следующего сообщения
    update_conversation(chat_id, user_id, response.id)

    # Возвращаем полный response объект для обработки citations
    return response


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик сообщений."""
    try:
        if not update.effective_chat or not update.effective_user or not update.message:
            logging.warning("Получено обновление без необходимых атрибутов")
            return

        # Обновление информации о чате
        chat = update.effective_chat
        chat_manager.update_chat(
            chat_id=chat.id,
            chat_type=chat.type,
            name=(
                chat.title
                if chat.title
                else f"Private chat with {update.effective_user.username}"
            ),
        )

        # Проверяем, должен ли бот ответить на это сообщение
        if not await should_bot_respond(update.message, context):
            return

        user = update.effective_user
        username = user.username
        user_id = user.id

        # Проверка доступа пользователя
        if USERS != "*":
            if username is None or username not in USERS:
                await update.message.reply_text("У вас нет доступа к боту.")
                return

        # Rate limiting
        if not check_rate_limit(user_id):
            await update.message.reply_text(
                f"Слишком много сообщений. Подождите немного ({RATE_LIMIT_WINDOW} сек)."
            )
            return

        # Валидация длины сообщения
        message_text = update.message.text
        if not message_text:
            return

        if len(message_text) > MAX_MESSAGE_LENGTH:
            await update.message.reply_text(
                f"Сообщение слишком длинное. Максимум: {MAX_MESSAGE_LENGTH} символов."
            )
            return

        # Отправка "печатает..."
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, action=ChatAction.TYPING
            )
        except Forbidden:
            logging.warning(f"User {update.effective_chat.id} blocked the bot")
            return

        # Отправка в OpenAI Responses API
        chat_id = update.effective_chat.id
        response = await process_with_responses(chat_id, user_id, message_text)

        # Обрабатываем citations и отправляем ответ
        processed = await process_response_with_citations(response)
        await send_formatted_reply(update.message, processed)

    except Exception as e:
        logging.exception(f"Error in handle_message: {type(e).__name__}: {e}")
        sentry_sdk.capture_exception(e)
        try:
            if update.message:
                await update.message.reply_text(
                    "Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте позже."
                )
        except Exception as reply_error:
            logging.error(f"Ошибка при отправке сообщения об ошибке: {reply_error}")


async def reset_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /reset - сброс conversation пользователя."""
    try:
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if delete_user_conversation(chat_id, user_id):
            await update.message.reply_text("История диалога очищена.")
        else:
            await update.message.reply_text("У вас нет активного диалога.")

    except Exception as e:
        logging.error(f"Ошибка в reset_conversation: {e}")
        await update.message.reply_text("Произошла ошибка при сбросе диалога.")


async def get_chat_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /chatinfo - информация о чате."""
    chat = update.effective_chat
    user = update.effective_user

    info_message = (
        f"Информация о чате:\n"
        f"ID чата: {chat.id}\n"
        f"Тип чата: {chat.type}\n"
        f"Название: {chat.title if chat.title else 'Личный чат'}\n\n"
        f"Информация о пользователе:\n"
        f"ID пользователя: {user.id}\n"
        f"Username: @{user.username if user.username else 'отсутствует'}"
    )

    await update.message.reply_text(info_message)
