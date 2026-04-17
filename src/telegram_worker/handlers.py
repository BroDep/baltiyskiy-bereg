from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from src.telegram_worker.service import FALLBACK_RESPONSE_TEXT, TelegramChatService

logger = logging.getLogger(__name__)

START_RESPONSE_TEXT = (
    "Здравствуйте! Я Telegram-бот сервис-деска «Балтийский Берег». "
    "Отправьте сообщение, и я передам его в backend."
)
HELP_RESPONSE_TEXT = (
    "Доступные команды:\n"
    "/start — приветствие\n"
    "/help — помощь\n"
    "/ping — проверка соединения\n\n"
    "Просто отправьте текстовый вопрос."
)
PING_RESPONSE_TEXT = "telegram-worker: ok"


async def handle_start(message: Message) -> None:
    await message.answer(START_RESPONSE_TEXT)


async def handle_help(message: Message) -> None:
    await message.answer(HELP_RESPONSE_TEXT)


async def handle_ping(message: Message) -> None:
    await message.answer(PING_RESPONSE_TEXT)


async def handle_text_message(
    message: Message,
    chat_service: TelegramChatService,
) -> None:
    text = (message.text or "").strip()
    if not text:
        logger.info("Skipping empty Telegram text message update")
        return

    from_user = message.from_user
    if from_user is None:
        logger.warning("Skipping Telegram message without from_user")
        return

    try:
        response_text = await chat_service.get_reply(
            message_text=text,
            telegram_user_id=from_user.id,
        )
    except Exception:
        logger.exception("Unexpected Telegram handler failure")
        response_text = FALLBACK_RESPONSE_TEXT

    await message.answer(response_text)


def build_router(chat_service: TelegramChatService) -> Router:
    router = Router(name="telegram-worker")

    @router.message(CommandStart())
    async def on_start(message: Message) -> None:
        await handle_start(message)

    @router.message(Command("help"))
    async def on_help(message: Message) -> None:
        await handle_help(message)

    @router.message(Command("ping", "health"))
    async def on_ping(message: Message) -> None:
        await handle_ping(message)

    @router.message(F.text)
    async def on_text(message: Message) -> None:
        await handle_text_message(message, chat_service)

    return router
