from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.dependencies import ConfigurableProbeState, DependencyProbe, ReadinessService
from src.api.routes import FAILURE_SENTINEL
from src.main import create_app


def build_client(mode: str = "ready") -> TestClient:
    probe_state = ConfigurableProbeState(mode=mode)
    readiness_service = ReadinessService(
        probes=[DependencyProbe(name=probe_state.name, evaluator=probe_state.evaluate)]
    )
    return TestClient(create_app(readiness_service=readiness_service))


def test_chat_returns_deterministic_stub_response() -> None:
    client = build_client()

    response = client.post(
        "/api/chat",
        json={"message": "hello", "correlation_id": "corr-123", "source": "telegram"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "response_text": "Stub reply: hello",
        "correlation_id": "corr-123",
    }


def test_chat_generates_fallback_correlation_id_when_absent() -> None:
    client = build_client()

    response = client.post("/api/chat", json={"message": "hello"})

    assert response.status_code == 200
    assert response.json()["correlation_id"] == "generated-by-api"


def test_chat_rejects_empty_json_body() -> None:
    client = build_client()

    response = client.post("/api/chat", json={})

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(error["loc"][-1] == "message" for error in errors)


def test_chat_rejects_wrong_field_types() -> None:
    client = build_client()

    response = client.post("/api/chat", json={"message": 123})

    assert response.status_code == 422


def test_chat_rejects_oversized_optional_metadata() -> None:
    client = build_client()

    response = client.post(
        "/api/chat",
        json={"message": "hello", "source": "x" * 257},
    )

    assert response.status_code == 422


def test_chat_accepts_max_length_message_without_internal_error() -> None:
    client = build_client()

    response = client.post("/api/chat", json={"message": "x" * 4000})

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["response_text"] == f"Stub reply: {'x' * 4000}"


def test_chat_returns_controlled_failure_shape_for_sentinel_message() -> None:
    client = build_client()

    response = client.post(
        "/api/chat",
        json={"message": FAILURE_SENTINEL, "correlation_id": "corr-fail"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "error_code": "CHAT_UNAVAILABLE",
        "message": "The chat service is temporarily unavailable. Please try again later.",
        "correlation_id": "corr-fail",
    }


def test_liveness_is_process_only() -> None:
    client = build_client(mode="error")

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_returns_ready_when_probe_is_healthy() -> None:
    client = build_client(mode="ready")

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dependencies": [
            {
                "name": "chat-backend",
                "status": "ready",
                "detail": "dependency ready",
            }
        ],
    }


def test_readiness_returns_degraded_when_probe_errors() -> None:
    client = build_client(mode="error")

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "dependencies": [
            {
                "name": "chat-backend",
                "status": "degraded",
                "detail": "dependency probe failed",
            }
        ],
    }


def test_readiness_returns_degraded_when_probe_times_out() -> None:
    client = build_client(mode="timeout")

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json()["dependencies"][0] == {
        "name": "chat-backend",
        "status": "degraded",
        "detail": "dependency probe timed out",
    }


def test_readiness_normalizes_malformed_probe_results() -> None:
    client = build_client(mode="malformed")

    first = client.get("/health/ready")
    second = client.get("/health/ready")

    assert first.status_code == 503
    assert second.status_code == 503
    assert first.json() == second.json()
    assert first.json()["dependencies"][0] == {
        "name": "chat-backend",
        "status": "degraded",
        "detail": "dependency probe returned malformed result",
    }
