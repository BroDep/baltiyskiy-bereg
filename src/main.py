from __future__ import annotations

import uvicorn

from src.api import create_app
from src.config import get_settings

app = create_app()


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_reload,
    )


if __name__ == "__main__":
    main()
