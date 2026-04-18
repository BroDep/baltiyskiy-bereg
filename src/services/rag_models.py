from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

SourceType = Literal["ticket", "kb"]


@dataclass(slots=True)
class RagDocument:
    point_id: str
    source_type: SourceType
    source_id: int
    chunk_index: int
    title: str
    content: str
    citation_label: str
    excerpt: str
    metadata: dict[str, Any]
    changed_at: datetime | None = None


@dataclass(slots=True)
class RetrievedDocument(RagDocument):
    vector_score: float = 0.0
    rerank_score: float | None = None
    final_score: float | None = None


@dataclass(slots=True)
class Citation:
    label: str
    source_type: SourceType
    source_id: int
    title: str
    excerpt: str


@dataclass(slots=True)
class GroundedAnswer:
    reply: str
    citations: list[Citation] = field(default_factory=list)
    confidence: float = 0.0
    grounded: bool = False
    needs_human: bool = True
    reason: str | None = None
    retrieval_confidence: float = 0.0
    verification_confidence: float = 0.0


@dataclass(slots=True)
class SyncSummary:
    full_sync: bool
    ticket_documents: int = 0
    kb_documents: int = 0


@dataclass(slots=True)
class SyncStatus:
    ready: bool = False
    running: bool = False
    last_sync_started_at: datetime | None = None
    last_sync_finished_at: datetime | None = None
    last_sync_success: bool = False
    last_error: str | None = None
    indexed_documents: int = 0
