from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.logging_setup import setup_logging
from src.services.telegram_bot import TelegramBotService
from src.services.yandex_gpt import YandexGPTClient, YandexGPTError

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    system_prompt: str | None = Field(default=None, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    setup_logging(app_settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = app_settings
        app.state.yandex_client = YandexGPTClient(app_settings)
        app.state.telegram_service = TelegramBotService(
            settings=app_settings,
            yandex_client=app.state.yandex_client,
        )

        if app.state.telegram_service is not None:
            await app.state.telegram_service.start()

        yield

        if app.state.telegram_service is not None:
            await app.state.telegram_service.stop()

        await app.state.yandex_client.aclose()

    app = FastAPI(title=app_settings.app_name, lifespan=lifespan)

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
        return JSONResponse(
            status_code=502,
            content={"detail": str(exc)},
        )

    @app.get("/")
    async def root() -> dict[str, str]:
        return {"message": "Baltiyskiy Bereg Bot API is running"}

    @app.get("/health")
    async def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "telegram_bot_enabled": app_settings.telegram_bot_enabled,
        }

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(payload: ChatRequest, request: Request) -> ChatResponse:
        yandex_client: YandexGPTClient = request.app.state.yandex_client
        try:
            reply = await yandex_client.generate_reply(
                message=payload.message,
                system_prompt=payload.system_prompt,
            )
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return ChatResponse(reply=reply)

    return app
