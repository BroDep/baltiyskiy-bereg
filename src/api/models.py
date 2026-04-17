from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ── Chat ──────────────────────────────────────────────────────────────────────

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
    confidence_label: str
    escalate: bool
    sources: list[Source]
    session_id: str


class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    vector_store_connected: bool
    version: str = "0.1.0"


# ── Analytics ─────────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total: int
    resolved: int
    escalated: int
    escalation_rate: float
    avg_confidence: float


class HourlyPoint(BaseModel):
    hour: int
    count: int


class DailyPoint(BaseModel):
    date: str
    total: int
    escalated: int


class TicketItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    message: str
    answer: str
    confidence_score: float
    confidence_label: str
    escalated: bool
    created_at: datetime


class TicketsResponse(BaseModel):
    total: int
    page: int
    pages: int
    items: list[TicketItem]
