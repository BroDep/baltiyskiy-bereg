from __future__ import annotations

from aiogram import Dispatcher

from src.telegram_worker.handlers import build_router
from src.telegram_worker.service import TelegramChatService


def create_dispatcher(chat_service: TelegramChatService) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(chat_service))
    return dispatcher
