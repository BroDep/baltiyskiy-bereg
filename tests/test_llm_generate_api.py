from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.config import YandexGPTConfig, load_config
from src.main import create_app
from src.services.llm import (
    LLMRequest,
    LLMResponse,
    LLMServiceError,
    LLMServiceTimeoutError,
    YandexGPTGateway,
)
from src.settings.models import LLMSettings


class RecordingLLMService:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            response_text=f"Echo: {request.prompt}",
            model_name=request.settings.model_name,
            correlation_id=request.correlation_id,
            prompt_tokens=11,
            completion_tokens=7,
        )


class TimeoutLLMService:
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise LLMServiceTimeoutError("upstream timeout")


class FailingLLMService:
    def generate(self, request: LLMRequest) -> LLMResponse:
        raise LLMServiceError("upstream unavailable")


def test_generate_endpoint_returns_response_and_metadata_from_mock_service(
    tmp_path: Path,
) -> None:
    llm_service = RecordingLLMService()
    client = _build_client(tmp_path, llm_service)

    response = client.post(
        "/api/llm/generate",
        json={"message": "Привет", "correlation_id": "corr-42"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "response_text": "Echo: Привет",
        "metadata": {
            "model_name": "yandexgpt/latest",
            "correlation_id": "corr-42",
            "prompt_tokens": 11,
            "completion_tokens": 7,
        },
    }
    assert (
        llm_service.requests[0].system_prompt
        == "Ты внутренний ассистент сервис-деска Балтийский Берег."
    )
    assert llm_service.requests[0].settings.model_name == "yandexgpt/latest"


def test_generate_endpoint_maps_timeout_to_gateway_timeout(tmp_path: Path) -> None:
    client = _build_client(tmp_path, TimeoutLLMService())

    response = client.post(
        "/api/llm/generate",
        json={"prompt": "Привет", "correlation_id": "corr-timeout"},
    )

    assert response.status_code == 504
    assert response.json() == {
        "status": "error",
        "error_code": "LLM_TIMEOUT",
        "message": "YandexGPT request timed out.",
        "correlation_id": "corr-timeout",
    }


def test_generate_endpoint_maps_upstream_errors_to_bad_gateway(tmp_path: Path) -> None:
    client = _build_client(tmp_path, FailingLLMService())

    response = client.post(
        "/api/llm/generate",
        json={"prompt": "Привет", "correlation_id": "corr-fail"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "status": "error",
        "error_code": "LLM_UNAVAILABLE",
        "message": "YandexGPT request failed.",
        "correlation_id": "corr-fail",
    }


def test_generate_endpoint_accepts_response_longer_than_4000_chars(
    tmp_path: Path,
) -> None:
    client = _build_client(tmp_path, LongResponseLLMService())

    response = client.post(
        "/api/llm/generate",
        json={"prompt": "Привет", "correlation_id": "corr-long"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "response_text": "y" * 4001,
        "metadata": {
            "model_name": "yandexgpt/latest",
            "correlation_id": "corr-long",
            "prompt_tokens": None,
            "completion_tokens": None,
        },
    }


def test_yandex_gateway_maps_malformed_json_shape_to_service_error() -> None:
    gateway = YandexGPTGateway(
        YandexGPTConfig(
            api_key="test-key",
            folder_id="test-folder",
            model_name="yandexgpt/latest",
            base_url="https://llm.api.cloud.yandex.net",
            timeout_seconds=30.0,
        ),
        session=MalformedJSONSession(),
    )

    with pytest.raises(LLMServiceError, match="invalid response payload"):
        gateway.generate(
            LLMRequest(
                prompt="Привет",
                system_prompt="Системный промпт",
                settings=LLMSettings(
                    model_name="yandexgpt/latest",
                    temperature=0.2,
                    max_tokens=512,
                    timeout_seconds=30.0,
                ),
                correlation_id="corr-malformed",
            )
        )


class LongResponseLLMService:
    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            response_text="y" * 4001,
            model_name=request.settings.model_name,
            correlation_id=request.correlation_id,
        )


class MalformedResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> list[object]:
        return []


class MalformedJSONSession:
    def post(self, **_: object) -> MalformedResponse:
        return MalformedResponse()


def _build_client(tmp_path: Path, llm_service: object) -> TestClient:
    config = load_config({"SETTINGS_DATABASE_PATH": str(tmp_path / "settings.sqlite3")})
    return TestClient(create_app(config=config, llm_service=llm_service))
