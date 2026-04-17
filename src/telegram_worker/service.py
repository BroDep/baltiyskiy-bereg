from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from src.telegram_worker.client import (
    BackendProtocolError,
    BackendTimeoutError,
    BackendUnavailableError,
)

logger = logging.getLogger(__name__)

FALLBACK_RESPONSE_TEXT = "Сервис временно недоступен, попробуйте позже."


@dataclass(frozen=True, slots=True)
class TelegramReply:
    response_text: str
    correlation_id: str


class TelegramBackendClient(Protocol):
    async def send_message(
        self,
        *,
        message_text: str,
        correlation_id: str,
        user_id: str,
    ) -> TelegramReply:
        """Forward a Telegram message to the backend and return its reply."""


class TelegramChatService:
    """Application service for Telegram -> FastAPI chat relay."""

    def __init__(
        self,
        *,
        backend_client: TelegramBackendClient,
        correlation_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._backend_client = backend_client
        self._correlation_id_factory = correlation_id_factory or generate_correlation_id

    async def get_reply(self, *, message_text: str, telegram_user_id: int) -> str:
        correlation_id = self._correlation_id_factory()
        try:
            response = await self._backend_client.send_message(
                message_text=message_text,
                correlation_id=correlation_id,
                user_id=str(telegram_user_id),
            )
        except (BackendTimeoutError, BackendUnavailableError, BackendProtocolError):
            logger.warning(
                "Telegram worker returned fallback for correlation_id=%s",
                correlation_id,
            )
            return FALLBACK_RESPONSE_TEXT

        return response.response_text


def generate_correlation_id() -> str:
    return uuid4().hex
