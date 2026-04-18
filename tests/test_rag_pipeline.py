from __future__ import annotations

from src.config import Settings
from src.services.rag_models import RetrievedDocument, SyncStatus
from src.services.rag_pipeline import RagPipeline


class StubYandexClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self._responses = responses

    async def embed_text(self, text: str, *, kind: str) -> list[float]:
        return [0.1, 0.2, 0.3]

    async def generate_json(self, **_: object) -> dict[str, object]:
        return self._responses.pop(0)


class StubQdrantStore:
    def __init__(self, documents: list[RetrievedDocument]) -> None:
        self._documents = documents

    def search(
        self,
        query_vector: list[float],
        *,
        limit: int,
        score_threshold: float,
    ) -> list[RetrievedDocument]:
        return self._documents[:limit]


class StubSyncService:
    async def get_status(self) -> SyncStatus:
        return SyncStatus(
            ready=True,
            running=False,
            last_sync_success=True,
            indexed_documents=10,
        )


def build_settings() -> Settings:
    return Settings(
        rag_enabled=True,
        telegram_bot_enabled=False,
        yandex_gpt_api_key="test-api-key",
        yandex_gpt_folder_id="test-folder",
        yandex_gpt_model="yandexgpt/latest",
    )


def build_documents() -> list[RetrievedDocument]:
    return [
        RetrievedDocument(
            point_id="kb:101:0",
            source_type="kb",
            source_id=101,
            chunk_index=0,
            title="UniVPN и 2MFA",
            content="Проверьте UniVPN и 2MFA Контур.Коннект.",
            citation_label="KB#101",
            excerpt="Проверьте UniVPN и 2MFA Контур.Коннект.",
            metadata={"published": True},
            vector_score=0.82,
        ),
        RetrievedDocument(
            point_id="ticket:555:0",
            source_type="ticket",
            source_id=555,
            chunk_index=0,
            title="Не подключается удаленка",
            content="Пользователь не подключается к удаленке, помогла проверка UniVPN.",
            citation_label="TICKET#555",
            excerpt="Пользователь не подключается к удаленке.",
            metadata={"is_closed": True},
            vector_score=0.74,
        ),
    ]


async def test_pipeline_returns_safe_refusal_when_no_hits() -> None:
    pipeline = RagPipeline(
        settings=build_settings(),
        yandex_client=StubYandexClient([]),
        qdrant_store=StubQdrantStore([]),
        rag_sync_service=StubSyncService(),
    )

    answer = await pipeline.answer("Где инструкция по удаленке?")

    assert answer.grounded is False
    assert answer.needs_human is True
    assert answer.reason == "no_retrieval_hits"


async def test_pipeline_returns_grounded_answer_with_citations() -> None:
    pipeline = RagPipeline(
        settings=build_settings(),
        yandex_client=StubYandexClient(
            [
                {"scores": [{"id": "S1", "score": 0.91}, {"id": "S2", "score": 0.65}]},
                {
                    "answerable": True,
                    "answer": "Проверьте UniVPN и 2MFA Контур.Коннект. [S1]",
                    "used_source_ids": ["S1"],
                    "confidence": 0.92,
                    "needs_human": False,
                    "reason": "grounded",
                },
                {
                    "grounded": True,
                    "confidence": 0.95,
                    "unsupported_claims": [],
                    "reason": "verified",
                },
            ]
        ),
        qdrant_store=StubQdrantStore(build_documents()),
        rag_sync_service=StubSyncService(),
    )

    answer = await pipeline.answer("Не подключается удаленка")

    assert answer.grounded is True
    assert answer.needs_human is False
    assert answer.citations[0].label == "KB#101"
    assert "[KB#101]" in answer.reply
    assert answer.confidence >= 0.7


async def test_pipeline_refuses_when_verifier_finds_unsupported_claims() -> None:
    pipeline = RagPipeline(
        settings=build_settings(),
        yandex_client=StubYandexClient(
            [
                {"scores": [{"id": "S1", "score": 0.91}, {"id": "S2", "score": 0.65}]},
                {
                    "answerable": True,
                    "answer": "Переустановите VPN-клиент и проверьте роутер. [S1]",
                    "used_source_ids": ["S1"],
                    "confidence": 0.89,
                    "needs_human": False,
                    "reason": "drafted",
                },
                {
                    "grounded": False,
                    "confidence": 0.2,
                    "unsupported_claims": ["В источнике нет совета про роутер"],
                    "reason": "unsupported_claims",
                },
            ]
        ),
        qdrant_store=StubQdrantStore(build_documents()),
        rag_sync_service=StubSyncService(),
    )

    answer = await pipeline.answer("Не подключается удаленка")

    assert answer.grounded is False
    assert answer.needs_human is True
    assert answer.reason == "unsupported_claims"
