from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.dependencies import ReadinessService
from src.api.models import (
    ApiChatRequest,
    ChatErrorResponse,
    ChatSuccessResponse,
    GenerateErrorResponse,
    GenerateRequest,
    GenerateResponseMetadata,
    GenerateSuccessResponse,
    LiveResponse,
    ReadyResponse,
    RemoteHealthResponse,
)
from src.services.llm import (
    LLMRequest,
    LLMService,
    LLMServiceError,
    LLMServiceTimeoutError,
)
from src.settings.repository import SettingsRepository

FAILURE_SENTINEL = "__force_chat_failure__"

router = APIRouter()


def get_readiness_service() -> (
    ReadinessService
):  # pragma: no cover - replaced by app state in create_app
    raise RuntimeError("Readiness service dependency is not configured")


def get_settings_repository() -> (
    SettingsRepository
):  # pragma: no cover - replaced by app state
    raise RuntimeError("Settings repository dependency is not configured")


def get_llm_service() -> LLMService:  # pragma: no cover - replaced by app state
    raise RuntimeError("LLM service dependency is not configured")


@router.post(
    "/api/chat",
    response_model=ChatSuccessResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ChatErrorResponse}},
)
def post_chat(payload: ApiChatRequest) -> ChatSuccessResponse:
    correlation_id = payload.correlation_id or "generated-by-api"

    if payload.message == FAILURE_SENTINEL:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ChatErrorResponse(correlation_id=correlation_id).model_dump(),
        )

    response_text = f"Stub reply: {payload.message}"
    return ChatSuccessResponse(
        response_text=response_text, correlation_id=correlation_id
    )


@router.post(
    "/api/llm/generate",
    response_model=GenerateSuccessResponse,
    responses={
        status.HTTP_502_BAD_GATEWAY: {"model": GenerateErrorResponse},
        status.HTTP_504_GATEWAY_TIMEOUT: {"model": GenerateErrorResponse},
    },
)
def generate_llm_response(
    payload: GenerateRequest,
    settings_repository: SettingsRepository = Depends(get_settings_repository),
    llm_service: LLMService = Depends(get_llm_service),
) -> GenerateSuccessResponse:
    correlation_id = payload.correlation_id or "generated-by-api"
    system_prompt = settings_repository.get_system_prompt().prompt
    llm_settings = settings_repository.get_llm_settings()

    try:
        result = llm_service.generate(
            LLMRequest(
                prompt=payload.resolved_prompt,
                system_prompt=system_prompt,
                settings=llm_settings,
                correlation_id=correlation_id,
            )
        )
    except LLMServiceTimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=GenerateErrorResponse(
                error_code="LLM_TIMEOUT",
                message="YandexGPT request timed out.",
                correlation_id=correlation_id,
            ).model_dump(),
        ) from None
    except LLMServiceError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=GenerateErrorResponse(
                error_code="LLM_UNAVAILABLE",
                message="YandexGPT request failed.",
                correlation_id=correlation_id,
            ).model_dump(),
        ) from None

    return GenerateSuccessResponse(
        response_text=result.response_text,
        metadata=GenerateResponseMetadata(
            model_name=result.model_name,
            correlation_id=result.correlation_id or correlation_id,
            prompt_tokens=result.prompt_tokens,
            completion_tokens=result.completion_tokens,
        ),
    )


@router.get("/health", response_model=RemoteHealthResponse)
def health() -> RemoteHealthResponse:
    return RemoteHealthResponse()


@router.get("/health/live", response_model=LiveResponse)
def health_live() -> LiveResponse:
    return LiveResponse()


@router.get(
    "/health/ready",
    response_model=ReadyResponse,
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadyResponse}},
)
def health_ready(
    readiness_service: ReadinessService = Depends(get_readiness_service),
) -> ReadyResponse:
    results = readiness_service.evaluate()
    status_value = (
        "ready" if all(result.status == "ready" for result in results) else "degraded"
    )
    response = ReadyResponse(
        status=status_value,
        dependencies=[
            {"name": result.name, "status": result.status, "detail": result.detail}
            for result in results
        ],
    )

    if status_value == "degraded":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.model_dump(),
        )

    return response
