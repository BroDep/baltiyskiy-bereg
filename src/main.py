from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.responses import JSONResponse

from src.api.dependencies import ReadinessService, build_default_readiness_service
from src.api.routes import router


def create_app(readiness_service: ReadinessService | None = None) -> FastAPI:
    app = FastAPI(title="baltiyskiy-bereg-api", version="0.1.0")
    app.state.readiness_service = readiness_service or build_default_readiness_service()

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

    app.include_router(router)
    app.dependency_overrides.clear()

    from src.api import routes as route_module

    app.dependency_overrides[route_module.get_readiness_service] = _get_readiness_service
    return app


app = create_app()
