from __future__ import annotations

import asyncio
import logging
import socket

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from src.config import AppConfig, load_config
from src.telegram_worker.app import create_dispatcher
from src.telegram_worker.client import BackendChatClient
from src.telegram_worker.service import TelegramChatService


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def create_bot_session() -> AiohttpSession:
    session = AiohttpSession()
    session._connector_init["family"] = socket.AF_INET
    return session


def build_runtime(config: AppConfig) -> tuple[Bot, Dispatcher, BackendChatClient]:
    if not config.telegram.bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured.")

    backend_client = BackendChatClient(
        base_url=config.telegram.backend_api_base_url,
        timeout_seconds=config.telegram.api_timeout_seconds,
    )
    chat_service = TelegramChatService(backend_client=backend_client)
    dispatcher = create_dispatcher(chat_service)
    bot = Bot(token=config.telegram.bot_token, session=create_bot_session())
    return bot, dispatcher, backend_client


async def run_polling(config: AppConfig | None = None) -> None:
    configure_logging()
    resolved_config = config or load_config()
    bot, dispatcher, backend_client = build_runtime(resolved_config)

    logging.getLogger(__name__).info(
        "Starting Telegram polling worker against %s",
        resolved_config.telegram.backend_api_base_url,
    )
    try:
        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )
    finally:
        await bot.session.close()
        await backend_client.aclose()


def main() -> None:
    asyncio.run(run_polling())


if __name__ == "__main__":
    main()
