from __future__ import annotations

import json

import httpx
import pytest

from src.config import Settings
from src.services.yandex_gpt import YandexGPTClient, YandexGPTError


@pytest.mark.asyncio
async def test_generate_reply_returns_text() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(
            status_code=200,
            json={
                "result": {
                    "alternatives": [
                        {"message": {"text": "Готово"}},
                    ]
                }
            },
        )

    settings = Settings(
        telegram_bot_enabled=False,
        yandex_gpt_api_key="test-api-key",
        yandex_gpt_folder_id="test-folder",
        yandex_gpt_model="yandexgpt/latest",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = YandexGPTClient(settings=settings, http_client=http_client)
        reply = await client.generate_reply("Привет")

    assert reply == "Готово"
    assert captured["headers"]["authorization"] == "Api-Key test-api-key"
    assert captured["payload"]["modelUri"] == "gpt://test-folder/yandexgpt/latest"
    assert captured["payload"]["messages"][1]["text"] == "Привет"


@pytest.mark.asyncio
async def test_generate_reply_raises_on_invalid_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"result": {"alternatives": []}})

    settings = Settings(
        telegram_bot_enabled=False,
        yandex_gpt_api_key="test-api-key",
        yandex_gpt_folder_id="test-folder",
        yandex_gpt_model="yandexgpt/latest",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = YandexGPTClient(settings=settings, http_client=http_client)
        with pytest.raises(YandexGPTError):
            await client.generate_reply("Привет")
