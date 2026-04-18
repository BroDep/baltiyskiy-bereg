from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message

from src.config import Settings
from src.services.rag_pipeline import RagPipeline
from src.services.yandex_gpt import YandexGPTError

logger = logging.getLogger(__name__)


class TelegramBotService:
    def __init__(self, settings: Settings, rag_pipeline: RagPipeline) -> None:
        self._settings = settings
        self._rag_pipeline = rag_pipeline
        self._dispatcher = Dispatcher()
        self._bot: Bot | None = None
        self._polling_task: asyncio.Task[None] | None = None
        self._register_handlers()

    def _register_handlers(self) -> None:
        self._dispatcher.message.register(self._handle_start, CommandStart())
        self._dispatcher.message.register(self._handle_text_message, F.text)
        self._dispatcher.message.register(self._handle_unsupported_message)

    async def _handle_start(self, message: Message) -> None:
        await message.answer(
            "Привет! Я отвечаю только по базе знаний и истории тикетов Балтийского Берега. "
            "Если данных не хватит, честно скажу об этом."
        )

    async def _handle_text_message(self, message: Message) -> None:
        incoming_text = message.text or ""
        logger.info(
            "Telegram message received: chat_id=%s user_id=%s message_length=%s",
            message.chat.id,
            message.from_user.id if message.from_user else "unknown",
            len(incoming_text),
        )

        try:
            answer = await self._rag_pipeline.answer(incoming_text)
        except YandexGPTError:
            logger.exception(
                "Failed to generate Telegram reply: chat_id=%s",
                message.chat.id,
            )
            await message.answer(
                "Не удалось получить ответ из RAG-пайплайна. Попробуйте еще раз чуть позже."
            )
            return

        reply_text = answer.reply
        if answer.citations:
            sources = "\n".join(
                f"- {citation.label}: {citation.title}"
                for citation in answer.citations[:4]
            )
            reply_text = f"{reply_text}\n\nИсточники:\n{sources}"

        await message.answer(reply_text)

    async def _handle_unsupported_message(self, message: Message) -> None:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")

    async def start(self) -> None:
        if not self._settings.telegram_bot_enabled:
            logger.info("Telegram bot is disabled by configuration")
            return

        self._settings.validate_telegram()

        if self._bot is None:
            self._bot = Bot(token=self._settings.telegram_bot_token_value)

        if self._polling_task and not self._polling_task.done():
            logger.info("Telegram bot polling is already running")
            return

        logger.info("Starting Telegram bot polling")
        self._polling_task = asyncio.create_task(
            self._dispatcher.start_polling(
                self._bot,
                allowed_updates=self._dispatcher.resolve_used_update_types(),
            )
        )

    async def stop(self) -> None:
        if self._polling_task is not None:
            self._polling_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._polling_task
            self._polling_task = None

        if self._bot is not None:
            await self._bot.session.close()
            self._bot = None

        logger.info("Telegram bot polling stopped")
