from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.logging_setup import setup_logging
from src.services.mssql_knowledge_base import MSSQLKnowledgeBase
from src.services.qdrant_store import QdrantStore
from src.services.rag_pipeline import RagPipeline
from src.services.rag_sync import RagSyncService
from src.services.telegram_bot import TelegramBotService
from src.services.yandex_gpt import YandexGPTClient, YandexGPTError

logger = logging.getLogger(__name__)
FRONTEND_BUILD_DIR = Path(__file__).resolve().parents[1] / "frontend" / "react-app" / "build"
FRONTEND_INDEX_FILE = FRONTEND_BUILD_DIR / "index.html"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class CitationResponse(BaseModel):
    label: str
    source_type: str
    source_id: int
    title: str
    excerpt: str


class ChatResponse(BaseModel):
    reply: str
    citations: list[CitationResponse]
    confidence: float
    grounded: bool
    needs_human: bool
    reason: str | None = None


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    setup_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = app_settings
        app.state.yandex_client = YandexGPTClient(app_settings)
        app.state.qdrant_store = QdrantStore(app_settings)
        app.state.knowledge_base = MSSQLKnowledgeBase(app_settings)
        app.state.rag_sync_service = RagSyncService(
            settings=app_settings,
            knowledge_base=app.state.knowledge_base,
            qdrant_store=app.state.qdrant_store,
            yandex_client=app.state.yandex_client,
        )
        app.state.rag_pipeline = RagPipeline(
            settings=app_settings,
            yandex_client=app.state.yandex_client,
            qdrant_store=app.state.qdrant_store,
            rag_sync_service=app.state.rag_sync_service,
        )
        app.state.telegram_service = TelegramBotService(
            settings=app_settings,
            rag_pipeline=app.state.rag_pipeline,
        )

        await app.state.rag_sync_service.start()
        if app.state.telegram_service is not None:
            await app.state.telegram_service.start()

        yield

        if app.state.telegram_service is not None:
            await app.state.telegram_service.stop()
        await app.state.rag_sync_service.stop()
        await app.state.yandex_client.aclose()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.frontend_cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(
            "HTTP request processed: method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.exception_handler(YandexGPTError)
    async def handle_yandex_gpt_error(_: Request, exc: YandexGPTError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/", response_model=None)
    async def root() -> FileResponse | dict[str, str]:
        if FRONTEND_INDEX_FILE.exists():
            return FileResponse(FRONTEND_INDEX_FILE)
        return {"message": "Baltiyskiy Bereg grounded support API is running"}

    @app.get("/health")
    async def health(request: Request) -> dict[str, str | bool | int | None]:
        sync_service: RagSyncService = request.app.state.rag_sync_service
        sync_status = await sync_service.get_status()
        return {
            "status": "ok",
            "telegram_bot_enabled": app_settings.telegram_bot_enabled,
            "rag_enabled": app_settings.rag_enabled,
            "rag_ready": sync_status.ready,
            "rag_sync_running": sync_status.running,
            "rag_last_sync_success": sync_status.last_sync_success,
            "rag_indexed_documents": sync_status.indexed_documents,
            "rag_last_error": sync_status.last_error,
        }

    @app.get("/api/health")
    async def api_health(request: Request) -> dict[str, str | bool | int | None]:
        return await health(request)

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        rag_pipeline: RagPipeline = request.app.state.rag_pipeline
        answer = await rag_pipeline.answer(payload.message)
        return ChatResponse(
            reply=answer.reply,
            citations=[CitationResponse(**citation.__dict__) for citation in answer.citations],
            confidence=answer.confidence,
            grounded=answer.grounded,
            needs_human=answer.needs_human,
            reason=answer.reason,
        )

    @app.get("/{full_path:path}", include_in_schema=False, response_model=None)
    async def frontend(full_path: str) -> FileResponse | JSONResponse:
        if full_path in {"api", "health"} or full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        if not FRONTEND_INDEX_FILE.exists():
            return JSONResponse(
                status_code=404,
                content={"detail": "Frontend build is not available"},
            )

        requested_path = (FRONTEND_BUILD_DIR / full_path).resolve()
        if requested_path.is_file() and requested_path.is_relative_to(FRONTEND_BUILD_DIR):
            return FileResponse(requested_path)

        return FileResponse(FRONTEND_INDEX_FILE)

    return app
