from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import requests

from src.config import YandexGPTConfig
from src.settings.models import LLMSettings


@dataclass(frozen=True, slots=True)
class LLMRequest:
    prompt: str
    system_prompt: str
    settings: LLMSettings
    correlation_id: str | None = None


@dataclass(frozen=True, slots=True)
class LLMResponse:
    response_text: str
    model_name: str
    correlation_id: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMService(Protocol):
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response for the provided prompt."""


class LLMServiceError(RuntimeError):
    """Base error raised by LLM integration layer."""


class LLMServiceTimeoutError(LLMServiceError):
    """Raised when the upstream LLM provider times out."""


class UnconfiguredLLMService:
    """Placeholder service used before YandexGPT gateway is wired in."""

    def generate(self, request: LLMRequest) -> LLMResponse:
        raise LLMServiceError(
            f"LLM gateway is not configured for model '{request.settings.model_name}'."
        )


class YandexGPTGateway:
    """Minimal YandexGPT HTTP gateway using the Foundation Models completion API."""

    def __init__(
        self,
        config: YandexGPTConfig,
        session: requests.Session | None = None,
    ) -> None:
        self._config = config
        self._session = session or requests.Session()

    def generate(self, request: LLMRequest) -> LLMResponse:
        if not self._config.api_key or not self._config.folder_id:
            raise LLMServiceError("YandexGPT credentials are not configured.")

        try:
            response = self._session.post(
                url=f"{self._config.base_url.rstrip('/')}/foundationModels/v1/completion",
                headers={
                    "Authorization": f"Api-Key {self._config.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "modelUri": self._build_model_uri(request.settings.model_name),
                    "completionOptions": {
                        "stream": False,
                        "temperature": request.settings.temperature,
                        "maxTokens": str(request.settings.max_tokens),
                    },
                    "messages": [
                        {"role": "system", "text": request.system_prompt},
                        {"role": "user", "text": request.prompt},
                    ],
                },
                timeout=request.settings.timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.Timeout as exc:
            raise LLMServiceTimeoutError("YandexGPT request timed out.") from exc
        except requests.RequestException as exc:
            raise LLMServiceError("YandexGPT request failed.") from exc
        except ValueError as exc:
            raise LLMServiceError("YandexGPT returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise LLMServiceError("YandexGPT returned invalid response payload.")

        result = payload.get("result", {})
        if not isinstance(result, dict):
            raise LLMServiceError("YandexGPT returned invalid response payload.")

        alternatives = result.get("alternatives") or []
        if not alternatives:
            raise LLMServiceError("YandexGPT returned no completion alternatives.")

        if not isinstance(alternatives[0], dict):
            raise LLMServiceError("YandexGPT returned invalid response payload.")

        message = alternatives[0].get("message", {})
        if not isinstance(message, dict):
            raise LLMServiceError("YandexGPT returned invalid response payload.")

        response_text = str(message.get("text", "")).strip()
        if not response_text:
            raise LLMServiceError("YandexGPT returned an empty completion.")

        usage = result.get("usage", {})
        if not isinstance(usage, dict):
            raise LLMServiceError("YandexGPT returned invalid response payload.")

        return LLMResponse(
            response_text=response_text,
            model_name=str(result.get("modelVersion") or request.settings.model_name),
            correlation_id=request.correlation_id,
            prompt_tokens=_coerce_optional_int(usage.get("inputTextTokens")),
            completion_tokens=_coerce_optional_int(usage.get("completionTokens")),
        )

    def _build_model_uri(self, model_name: str) -> str:
        if model_name.startswith("gpt://"):
            return model_name

        return f"gpt://{self._config.folder_id}/{model_name}"


def build_llm_service(config: YandexGPTConfig) -> LLMService:
    if not config.api_key or not config.folder_id:
        return UnconfiguredLLMService()

    return YandexGPTGateway(config=config)


def _coerce_optional_int(value: object) -> int | None:
    if value is None:
        return None

    return int(value)
