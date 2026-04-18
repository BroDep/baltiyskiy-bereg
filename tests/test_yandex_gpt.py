from __future__ import annotations

import json

import httpx
import pytest

from src.config import Settings
from src.services.yandex_gpt import YandexGPTClient, YandexGPTError


def build_settings() -> Settings:
    return Settings(
        rag_enabled=False,
        telegram_bot_enabled=False,
        yandex_gpt_api_key="test-api-key",
        yandex_gpt_folder_id="test-folder",
        yandex_gpt_model="yandexgpt/latest",
    )


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

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = YandexGPTClient(settings=build_settings(), http_client=http_client)
        reply = await client.generate_reply("Привет")

    assert reply == "Готово"
    assert captured["headers"]["authorization"] == "Api-Key test-api-key"
    assert captured["payload"]["modelUri"] == "gpt://test-folder/yandexgpt/latest"
    assert captured["payload"]["messages"][1]["text"] == "Привет"


@pytest.mark.asyncio
async def test_embed_text_returns_vector() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["payload"] = json.loads(request.content.decode())
        return httpx.Response(status_code=200, json={"embedding": [0.1, 0.2, 0.3]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = YandexGPTClient(settings=build_settings(), http_client=http_client)
        embedding = await client.embed_text("Удаленка", kind="query")

    assert embedding == [0.1, 0.2, 0.3]
    assert captured["path"].endswith("/textEmbedding")
    assert captured["payload"]["modelUri"] == "emb://test-folder/text-search-query/latest"
    assert captured["payload"]["text"] == "Удаленка"


@pytest.mark.asyncio
async def test_generate_json_parses_code_fence() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "result": {
                    "alternatives": [
                        {
                            "message": {
                                "text": "```json\n{\"grounded\": true, \"confidence\": 0.8}\n```"
                            }
                        },
                    ]
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = YandexGPTClient(settings=build_settings(), http_client=http_client)
        payload = await client.generate_json(messages=[{"role": "user", "text": "verifier"}])

    assert payload == {"grounded": True, "confidence": 0.8}


@pytest.mark.asyncio
async def test_generate_reply_raises_on_invalid_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={"result": {"alternatives": []}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = YandexGPTClient(settings=build_settings(), http_client=http_client)
        with pytest.raises(YandexGPTError):
            await client.generate_reply("Привет")
