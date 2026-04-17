from __future__ import annotations

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None


class Source(BaseModel):
    title: str
    excerpt: str
    score: float
    ticket_id: int | None = None
    kb_doc_id: int | None = None


class ChatResponse(BaseModel):
    answer: str
    confidence_score: float = Field(..., ge=0.0, le=10.0)
    confidence_label: str  # "high" | "medium" | "low"
    escalate: bool
    sources: list[Source]
    session_id: str


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    db_connected: bool
    vector_store_connected: bool
    version: str = "0.1.0"
