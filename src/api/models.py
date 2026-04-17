from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator
from typing_extensions import Annotated

MessageText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
CorrelationId = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)
]
MetadataValue = Annotated[str, StringConstraints(strip_whitespace=True, max_length=256)]


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: MessageText
    correlation_id: CorrelationId | None = Field(
        default=None,
        description="Optional caller-provided correlation id propagated across transports.",
    )
    user_id: MetadataValue | None = Field(
        default=None,
        description="Optional upstream user identifier.",
    )
    source: MetadataValue | None = Field(
        default=None,
        description="Optional transport/source identifier such as telegram.",
    )


class ChatSuccessResponse(BaseModel):
    status: Literal["ok"] = "ok"
    response_text: str = Field(..., min_length=1)
    correlation_id: str = Field(..., min_length=1, max_length=128)


class ChatErrorResponse(BaseModel):
    status: Literal["error"] = "error"
    error_code: Literal["CHAT_UNAVAILABLE"] = "CHAT_UNAVAILABLE"
    message: str = Field(
        default="The chat service is temporarily unavailable. Please try again later.",
        min_length=1,
        max_length=200,
    )
    correlation_id: str = Field(..., min_length=1, max_length=128)


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: MessageText | None = None
    message: MessageText | None = None
    correlation_id: CorrelationId | None = Field(
        default=None,
        description="Optional caller-provided correlation id propagated to logs and response metadata.",
    )

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


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class ReadyResponse(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: list[DependencyStatus]
