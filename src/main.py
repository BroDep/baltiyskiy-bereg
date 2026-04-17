from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from src.api.dependencies import ReadinessService, build_default_readiness_service
from src.api.routes import router
from src.config import AppConfig, load_config
from src.database.client import SQLiteDatabaseClient
from src.services.llm import LLMService, build_llm_service
from src.settings.repository import SettingsRepository, SQLiteSettingsRepository


def create_app(
    config: AppConfig | None = None,
    readiness_service: ReadinessService | None = None,
    settings_repository: SettingsRepository | None = None,
    llm_service: LLMService | None = None,
) -> FastAPI:
    resolved_config = config or load_config()
    resolved_settings_repository = settings_repository or SQLiteSettingsRepository(
        database_client=SQLiteDatabaseClient(resolved_config.settings_database_path),
        default_system_prompt=resolved_config.default_system_prompt,
        default_llm_settings=resolved_config.default_llm_settings,
    )
    resolved_llm_service = llm_service or build_llm_service(resolved_config.yandex)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings_repository.initialize()
        yield

    app = FastAPI(title=resolved_config.app_name, version="0.1.0", lifespan=lifespan)
    app.state.config = resolved_config
    app.state.readiness_service = readiness_service or build_default_readiness_service()
    app.state.settings_repository = resolved_settings_repository
    app.state.llm_service = resolved_llm_service

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_, exc: HTTPException) -> JSONResponse:
        if isinstance(exc.detail, dict):
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.get("/")
    def read_root() -> dict[str, str]:
        return {"message": "Hello from baltiyskiy-bereg!", "version": "1.0.0"}

    def _get_readiness_service() -> ReadinessService:
        return app.state.readiness_service

    def _get_settings_repository() -> SettingsRepository:
        return app.state.settings_repository

    def _get_llm_service() -> LLMService:
        return app.state.llm_service

    app.include_router(router)
    app.dependency_overrides.clear()

    from src.api import routes as route_module

    app.dependency_overrides[route_module.get_readiness_service] = (
        _get_readiness_service
    )
    app.dependency_overrides[route_module.get_settings_repository] = (
        _get_settings_repository
    )
    app.dependency_overrides[route_module.get_llm_service] = _get_llm_service
    return app


app = create_app()
