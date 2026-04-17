from __future__ import annotations

import asyncio
import json
import socket
from dataclasses import dataclass

import httpx
import pytest
from aiogram import Bot
from aiogram.types import Update

from src.telegram_worker.app import create_dispatcher
from src.telegram_worker.client import (
    BackendChatClient,
    BackendProtocolError,
    BackendTimeoutError,
    BackendUnavailableError,
)
from src.telegram_worker.handlers import (
    handle_help,
    handle_ping,
    handle_start,
    handle_text_message,
)
from src.telegram_worker.main import create_bot_session
from src.telegram_worker.service import FALLBACK_RESPONSE_TEXT, TelegramChatService


class FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class FakeMessage:
    def __init__(self, text: str | None, user_id: int = 321) -> None:
        self.text = text
        self.from_user = FakeUser(user_id)
        self.answers: list[str] = []

    async def answer(self, text: str) -> None:
        self.answers.append(text)


@dataclass(slots=True)
class FakeBackendReply:
    response_text: str
    correlation_id: str


class RecordingBackendClient:
    def __init__(
        self, *, response_text: str = "Готово", error: Exception | None = None
    ) -> None:
        self._response_text = response_text
        self._error = error
        self.calls: list[dict[str, str]] = []

    async def send_message(
        self,
        *,
        message_text: str,
        correlation_id: str,
        user_id: str,
    ) -> FakeBackendReply:
        self.calls.append(
            {
                "message_text": message_text,
                "correlation_id": correlation_id,
                "user_id": user_id,
            }
        )
        if self._error is not None:
            raise self._error

        return FakeBackendReply(
            response_text=self._response_text,
            correlation_id=correlation_id,
        )


def test_start_handler_returns_greeting() -> None:
    message = FakeMessage(text="/start")

    asyncio.run(handle_start(message))

    assert message.answers == [
        "Здравствуйте! Я Telegram-бот сервис-деска «Балтийский Берег». Отправьте сообщение, и я передам его в backend."
    ]


def test_help_handler_returns_supported_commands() -> None:
    message = FakeMessage(text="/help")

    asyncio.run(handle_help(message))

    assert message.answers == [
        "Доступные команды:\n/start — приветствие\n/help — помощь\n/ping — проверка соединения\n\nПросто отправьте текстовый вопрос."
    ]


def test_ping_handler_returns_transport_health() -> None:
    message = FakeMessage(text="/ping")

    asyncio.run(handle_ping(message))

    assert message.answers == ["telegram-worker: ok"]


def test_text_handler_returns_backend_reply_and_propagates_user_id() -> None:
    backend_client = RecordingBackendClient(response_text="Ответ из backend")
    service = TelegramChatService(
        backend_client=backend_client,
        correlation_id_factory=lambda: "corr-telegram-1",
    )
    message = FakeMessage(text="Где инструкция по VPN?", user_id=777)

    asyncio.run(handle_text_message(message, service))

    assert message.answers == ["Ответ из backend"]
    assert backend_client.calls == [
        {
            "message_text": "Где инструкция по VPN?",
            "correlation_id": "corr-telegram-1",
            "user_id": "777",
        }
    ]


@pytest.mark.parametrize(
    ("error",),
    [
        (BackendTimeoutError("timeout"),),
        (BackendUnavailableError("unavailable"),),
        (BackendProtocolError("bad-payload"),),
    ],
)
def test_chat_service_returns_fallback_on_backend_failures(error: Exception) -> None:
    service = TelegramChatService(
        backend_client=RecordingBackendClient(error=error),
        correlation_id_factory=lambda: "corr-fallback",
    )

    response_text = asyncio.run(
        service.get_reply(message_text="Нужна помощь", telegram_user_id=42)
    )

    assert response_text == FALLBACK_RESPONSE_TEXT


def test_backend_client_posts_telegram_chat_payload() -> None:
    captured_request: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_request["method"] = request.method
        captured_request["url"] = str(request.url)
        captured_request["json"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            status_code=200,
            json={
                "status": "ok",
                "response_text": "Решение найдено",
                "correlation_id": "corr-http-1",
            },
        )

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://backend.local",
        ) as session:
            client = BackendChatClient(
                base_url="http://backend.local",
                timeout_seconds=4.0,
                session=session,
            )

            response = await client.send_message(
                message_text="Где найти VPN?",
                correlation_id="corr-http-1",
                user_id="555",
            )

            assert response.response_text == "Решение найдено"

    asyncio.run(scenario())

    assert captured_request == {
        "method": "POST",
        "url": "http://backend.local/api/chat",
        "json": {
            "message": "Где найти VPN?",
            "correlation_id": "corr-http-1",
            "user_id": "555",
            "source": "telegram",
        },
    }


def test_backend_client_rejects_invalid_response_shape() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={"status": "ok", "correlation_id": "corr-http-2"},
        )

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://backend.local",
        ) as session:
            client = BackendChatClient(
                base_url="http://backend.local",
                timeout_seconds=4.0,
                session=session,
            )

            with pytest.raises(BackendProtocolError):
                await client.send_message(
                    message_text="Где найти VPN?",
                    correlation_id="corr-http-2",
                    user_id="555",
                )

    asyncio.run(scenario())


def test_dispatcher_ignores_empty_update_without_crashing() -> None:
    service = TelegramChatService(
        backend_client=RecordingBackendClient(),
        correlation_id_factory=lambda: "corr-dispatcher",
    )

    async def scenario() -> None:
        dispatcher = create_dispatcher(service)
        bot = Bot(token="42:TEST")
        try:
            await dispatcher.feed_update(
                bot,
                Update.model_validate(
                    {
                        "update_id": 1,
                        "message": {
                            "message_id": 1,
                            "date": 0,
                            "chat": {"id": 321, "type": "private"},
                            "from": {
                                "id": 321,
                                "is_bot": False,
                                "first_name": "Test",
                            },
                            "text": "",
                        },
                    }
                ),
            )
        finally:
            await bot.session.close()

    asyncio.run(scenario())


def test_create_bot_session_forces_ipv4_connector_family() -> None:
    session = create_bot_session()

    assert session._connector_init["family"] == socket.AF_INET
