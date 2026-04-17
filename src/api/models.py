from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing_extensions import Annotated

# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    session_id: str | None = None
    user_id: int | None = None


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


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    user_id: int
    username: str


# ── Chat history ──────────────────────────────────────────────────────────────

class MessageItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    meta: Any | None = None
    created_at: datetime


class HistoryResponse(BaseModel):
    items: list[MessageItem]
    has_more: bool


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


# ── Dev-branch API models (routes.py) ─────────────────────────────────────────

MessageText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
CorrelationId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]
MetadataValue = Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)]


class ApiChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: MessageText
    correlation_id: CorrelationId | None = Field(default=None)
    user_id: MetadataValue | None = Field(default=None)
    source: MetadataValue | None = Field(default=None)


class ChatSuccessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    response_text: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1, max_length=128)


class ChatErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error_code: Literal["CHAT_UNAVAILABLE"] = "CHAT_UNAVAILABLE"
    message: str = Field(default="The chat service is temporarily unavailable.", min_length=1, max_length=200)
    correlation_id: str = Field(..., min_length=1, max_length=128)


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: MessageText | None = None
    message: MessageText | None = None
    correlation_id: CorrelationId | None = Field(default=None)

    @model_validator(mode="after")
    def validate_prompt_fields(self) -> "GenerateRequest":
        if self.prompt is None and self.message is None:
            raise ValueError("Either 'prompt' or 'message' must be provided.")
        return self

    @property
    def resolved_prompt(self) -> str:
        return self.prompt or self.message or ""


class GenerateResponseMetadata(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=200)
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
    message: str = Field(..., min_length=1, max_length=200)
    correlation_id: str = Field(..., min_length=1, max_length=128)


class DependencyStatus(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    status: Literal["ready", "degraded"]
    detail: str = Field(..., min_length=1, max_length=200)


class LiveResponse(BaseModel):
    status: Literal["alive"] = "alive"


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: list[DependencyStatus]
