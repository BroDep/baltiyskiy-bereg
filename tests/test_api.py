from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from src.api import create_app
from src.config import Settings
from src.services.yandex_gpt import YandexGPTError


class StubYandexClient:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def generate_reply(
        self,
        message: str,
        system_prompt: str | None = None,
    ) -> str:
        if self.should_fail:
            raise YandexGPTError("upstream failed")
        suffix = f" [{system_prompt}]" if system_prompt else ""
        return f"echo: {message}{suffix}"

    async def aclose(self) -> None:
        return None


def create_test_app(*, should_fail: bool = False):
    settings = Settings(
        telegram_bot_enabled=False,
        yandex_gpt_api_key="test-api-key",
        yandex_gpt_folder_id="test-folder",
        yandex_gpt_model="yandexgpt/latest",
    )
    app = create_app(settings)

    original_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan_with_stub(app_instance):
        async with original_lifespan(app_instance):
            app_instance.state.yandex_client = StubYandexClient(should_fail=should_fail)
            yield

    app.router.lifespan_context = lifespan_with_stub
    return app


def test_health_endpoint_returns_ok() -> None:
    app = create_test_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "telegram_bot_enabled": False}


def test_chat_endpoint_returns_reply() -> None:
    app = create_test_app()

    with TestClient(app) as client:
        response = client.post(
            "/api/chat",
            json={"message": "Привет", "system_prompt": "Скажи коротко"},
        )

    assert response.status_code == 200
    assert response.json() == {"reply": "echo: Привет [Скажи коротко]"}


def test_chat_endpoint_returns_502_on_yandex_error() -> None:
    app = create_test_app(should_fail=True)

    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Привет"})

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream failed"}
