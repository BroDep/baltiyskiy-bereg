from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BackendChatReply:
    response_text: str
    correlation_id: str


class BackendChatError(RuntimeError):
    """Base error raised by Telegram worker backend transport."""


class BackendTimeoutError(BackendChatError):
    """Raised when the FastAPI backend times out."""


class BackendUnavailableError(BackendChatError):
    """Raised when the FastAPI backend is unavailable."""


class BackendProtocolError(BackendChatError):
    """Raised when the FastAPI backend returns an invalid contract."""


class BackendChatClient:
    """HTTP client for forwarding Telegram messages to the FastAPI backend."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        session: httpx.AsyncClient | None = None,
    ) -> None:
        self._chat_endpoint = f"{base_url.rstrip('/')}/api/chat"
        self._timeout_seconds = timeout_seconds
        self._owns_session = session is None
        self._session = session or httpx.AsyncClient(timeout=timeout_seconds)

    async def send_message(
        self,
        *,
        message_text: str,
        correlation_id: str,
        user_id: str,
    ) -> BackendChatReply:
        try:
            response = await self._session.post(
                self._chat_endpoint,
                json={
                    "message": message_text,
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "source": "telegram",
                },
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            logger.warning(
                "Telegram worker backend timeout for correlation_id=%s",
                correlation_id,
            )
            raise BackendTimeoutError("Backend chat request timed out.") from exc
        except httpx.HTTPError as exc:
            logger.warning(
                "Telegram worker backend transport error for correlation_id=%s",
                correlation_id,
            )
            raise BackendUnavailableError("Backend chat request failed.") from exc

        if response.status_code >= 500:
            logger.warning(
                "Telegram worker backend returned %s for correlation_id=%s",
                response.status_code,
                correlation_id,
            )
            raise BackendUnavailableError("Backend chat request failed.")

        if response.status_code >= 400:
            logger.warning(
                "Telegram worker backend returned unexpected status %s for correlation_id=%s",
                response.status_code,
                correlation_id,
            )
            raise BackendProtocolError(
                "Backend chat request returned unexpected status."
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise BackendProtocolError(
                "Backend chat request returned invalid JSON."
            ) from exc

        if not isinstance(payload, dict):
            raise BackendProtocolError("Backend chat request returned invalid payload.")

        if payload.get("status") != "ok":
            raise BackendProtocolError(
                "Backend chat request returned non-success status."
            )

        response_text = payload.get("response_text")
        response_correlation_id = payload.get("correlation_id")
        if not isinstance(response_text, str) or not response_text.strip():
            raise BackendProtocolError(
                "Backend chat request returned empty response text."
            )

        if (
            not isinstance(response_correlation_id, str)
            or not response_correlation_id.strip()
        ):
            raise BackendProtocolError(
                "Backend chat request returned invalid correlation id."
            )

        return BackendChatReply(
            response_text=response_text,
            correlation_id=response_correlation_id,
        )

    async def aclose(self) -> None:
        if self._owns_session:
            await self._session.aclose()
