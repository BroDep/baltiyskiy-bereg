from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

PromptText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)
]
ModelName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]


class SystemPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: PromptText


class LLMSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: ModelName
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=512, ge=1, le=8192)
    timeout_seconds: float = Field(default=30.0, gt=0.0, le=120.0)
