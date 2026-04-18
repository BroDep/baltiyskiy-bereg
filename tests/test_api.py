from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi.testclient import TestClient

from src.api import create_app
from src.config import Settings
from src.services.yandex_gpt import YandexGPTError


@dataclass
class StubCitation:
    label: str
    source_type: str
    source_id: int
    title: str
    excerpt: str


@dataclass
class StubAnswer:
    reply: str
    citations: list[StubCitation]
    confidence: float
    grounded: bool
    needs_human: bool
    reason: str | None = None


@dataclass
class StubSyncStatus:
    ready: bool = True
    running: bool = False
    last_sync_success: str | None = None
    indexed_documents: int = 0
    last_error: str | None = None


class StubRagPipeline:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def answer(self, message: str) -> StubAnswer:
        if self.should_fail:
            raise YandexGPTError("upstream failed")

        return StubAnswer(
            reply=f"echo: {message}",
            citations=[
                StubCitation(
                    label="ticket",
                    source_type="ticket",
                    source_id=101,
                    title="Тикет 101",
                    excerpt="Фрагмент ответа",
                )
            ],
            confidence=0.82,
            grounded=True,
            needs_human=False,
            reason=None,
        )


class StubSyncService:
    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def get_status(self) -> StubSyncStatus:
        return StubSyncStatus(
            ready=True,
            running=False,
            last_sync_success="2026-04-18T10:00:00Z",
            indexed_documents=42,
            last_error=None,
        )


def create_test_app(*, should_fail: bool = False):
    settings = Settings(
        telegram_bot_enabled=False,
        rag_enabled=True,
        rag_sync_on_startup=False,
        yandex_gpt_api_key="test-api-key",
        yandex_gpt_folder_id="test-folder",
        yandex_gpt_model="yandexgpt/latest",
        mssql_password="test-password",
    )
    app = create_app(settings)

    @asynccontextmanager
    async def lifespan_with_stub(app_instance):
        app_instance.state.rag_pipeline = StubRagPipeline(should_fail=should_fail)
        app_instance.state.rag_sync_service = StubSyncService()
        yield

    app.router.lifespan_context = lifespan_with_stub
    return app


def test_health_endpoint_returns_ok() -> None:
    app = create_test_app()

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "telegram_bot_enabled": False,
        "rag_enabled": True,
        "rag_ready": True,
        "rag_sync_running": False,
        "rag_last_sync_success": "2026-04-18T10:00:00Z",
        "rag_indexed_documents": 42,
        "rag_last_error": None,
    }


def test_api_health_endpoint_returns_ok() -> None:
    app = create_test_app()

    with TestClient(app) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["telegram_bot_enabled"] is False
    assert response.json()["rag_ready"] is True


def test_chat_endpoint_returns_reply() -> None:
    app = create_test_app()

    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Привет"})

    assert response.status_code == 200
    assert response.json() == {
        "reply": "echo: Привет",
        "citations": [
            {
                "label": "ticket",
                "source_type": "ticket",
                "source_id": 101,
                "title": "Тикет 101",
                "excerpt": "Фрагмент ответа",
            }
        ],
        "confidence": 0.82,
        "grounded": True,
        "needs_human": False,
        "reason": None,
    }


def test_chat_endpoint_returns_502_on_yandex_error() -> None:
    app = create_test_app(should_fail=True)

    with TestClient(app) as client:
        response = client.post("/api/chat", json={"message": "Привет"})

    assert response.status_code == 502
    assert response.json() == {"detail": "upstream failed"}
