from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)
    user_id: str | None = Field(default=None, min_length=1, max_length=128)
    source: str | None = Field(default=None, min_length=1, max_length=256)
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


class ChatSuccessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    response_text: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1, max_length=128)


class ChatErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error_code: Literal["CHAT_UNAVAILABLE"] = "CHAT_UNAVAILABLE"
    message: str = (
        "The chat service is temporarily unavailable. Please try again later."
    )
    correlation_id: str = Field(..., min_length=1, max_length=128)


class HealthResponse(BaseModel):
    status: str
    db_connected: bool | None = None
    vector_store_connected: bool | None = None
    version: str | None = None


class LiveResponse(BaseModel):
    status: Literal["alive"] = "alive"


class ReadyDependency(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    status: Literal["ready", "degraded"]
    detail: str = Field(..., min_length=1, max_length=256)


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: list[ReadyDependency]


class GenerateRequest(BaseModel):
    prompt: str | None = Field(default=None, min_length=1, max_length=4000)
    message: str | None = Field(default=None, min_length=1, max_length=4000)
    correlation_id: str | None = Field(default=None, min_length=1, max_length=128)

    @property
    def resolved_prompt(self) -> str:
        return self.prompt or self.message or ""


class GenerateResponseMetadata(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=128)
    correlation_id: str = Field(..., min_length=1, max_length=128)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)


class GenerateSuccessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    response_text: str = Field(..., min_length=1)
    metadata: GenerateResponseMetadata


class GenerateErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error_code: Literal["LLM_TIMEOUT", "LLM_UNAVAILABLE"]
    message: str = Field(..., min_length=1, max_length=256)
    correlation_id: str = Field(..., min_length=1, max_length=128)


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
