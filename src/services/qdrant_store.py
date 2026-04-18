from __future__ import annotations

from collections import defaultdict
from typing import Any, Sequence

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from src.config import Settings
from src.services.rag_models import RagDocument, RetrievedDocument


class QdrantStore:
    def __init__(
        self,
        settings: Settings,
        client: QdrantClient | None = None,
    ) -> None:
        self._settings = settings
        self._collection_name = settings.qdrant_collection_name
        self._client = client or QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key_value,
            timeout=settings.qdrant_timeout_seconds,
        )

    def ensure_collection(self, vector_size: int) -> None:
        if self._client.collection_exists(self._collection_name):
            return

        self._client.create_collection(
            collection_name=self._collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            on_disk_payload=True,
        )
        self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="source_type",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="source_id",
            field_schema=PayloadSchemaType.INTEGER,
        )
        self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="service_name",
            field_schema=PayloadSchemaType.KEYWORD,
        )
        self._client.create_payload_index(
            collection_name=self._collection_name,
            field_name="task_type_name",
            field_schema=PayloadSchemaType.KEYWORD,
        )

    def count_documents(self) -> int:
        if not self._client.collection_exists(self._collection_name):
            return 0
        return int(self._client.count(collection_name=self._collection_name, exact=True).count)

    def upsert_documents(
        self,
        documents: Sequence[RagDocument],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if not documents:
            return

        points = [
            PointStruct(
                id=document.point_id,
                vector=list(embedding),
                payload=self._document_to_payload(document),
            )
            for document, embedding in zip(documents, embeddings, strict=True)
        ]
        self._client.upsert(
            collection_name=self._collection_name,
            points=points,
            wait=True,
        )

    def replace_documents(
        self,
        documents: Sequence[RagDocument],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if not documents:
            return

        by_source: dict[tuple[str, int], list[tuple[RagDocument, Sequence[float]]]] = defaultdict(list)
        for document, embedding in zip(documents, embeddings, strict=True):
            by_source[(document.source_type, document.source_id)].append((document, embedding))

        for source_type, source_id in by_source:
            self.delete_source_documents(source_type=source_type, source_id=source_id)

        self.upsert_documents(documents, embeddings)

    def delete_source_documents(self, source_type: str, source_id: int) -> None:
        if not self._client.collection_exists(self._collection_name):
            return
        self._client.delete(
            collection_name=self._collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source_type",
                        match=MatchValue(value=source_type),
                    ),
                    FieldCondition(
                        key="source_id",
                        match=MatchValue(value=source_id),
                    ),
                ]
            ),
            wait=True,
        )

    def search(
        self,
        query_vector: Sequence[float],
        *,
        limit: int,
        score_threshold: float,
    ) -> list[RetrievedDocument]:
        if not self._client.collection_exists(self._collection_name):
            return []

        response = self._client.query_points(
            collection_name=self._collection_name,
            query=list(query_vector),
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )
        documents: list[RetrievedDocument] = []
        for point in response.points:
            payload = dict(point.payload or {})
            metadata = self._extract_metadata(payload)
            documents.append(
                RetrievedDocument(
                    point_id=str(point.id),
                    source_type=str(payload.get("source_type") or "ticket"),
                    source_id=int(payload.get("source_id") or 0),
                    chunk_index=int(payload.get("chunk_index") or 0),
                    title=str(payload.get("title") or ""),
                    content=str(payload.get("content") or ""),
                    citation_label=str(payload.get("citation_label") or ""),
                    excerpt=str(payload.get("excerpt") or ""),
                    metadata=metadata,
                    vector_score=float(point.score or 0.0),
                )
            )
        return documents

    def _document_to_payload(self, document: RagDocument) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_type": document.source_type,
            "source_id": document.source_id,
            "chunk_index": document.chunk_index,
            "title": document.title,
            "content": document.content,
            "citation_label": document.citation_label,
            "excerpt": document.excerpt,
        }
        if document.changed_at is not None:
            payload["changed_at"] = document.changed_at.isoformat()
        for key, value in document.metadata.items():
            sanitized = self._sanitize_payload_value(value)
            if sanitized is not None:
                payload[key] = sanitized
        return payload

    def _extract_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(payload)
        for key in (
            "source_type",
            "source_id",
            "chunk_index",
            "title",
            "content",
            "citation_label",
            "excerpt",
        ):
            metadata.pop(key, None)
        return metadata

    def _sanitize_payload_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, list):
            return [item for item in value if isinstance(item, (str, int, float, bool))]
        return str(value)
