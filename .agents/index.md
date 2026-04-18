# Project Index

## Project

- Baltiyskiy Bereg service desk assistant.
- Goal: help employees ask questions, describe incidents, and get solution hints from historical tickets and KB articles.

## Core Data Sources

- MSSQL database `service_desk_tdbb`.
- Main tables: `Task`, `TaskFieldValues`, `TaskExpenses`, `KBDocument`.

## Main Integrations

- MSSQL as read-only source of tickets and KB.
- Qdrant as the vector store for tickets and KB chunks.
- YandexGPT as LLM provider.
- Yandex AI Studio embeddings `text-search-doc/latest` and `text-search-query/latest` for retrieval.
- React web frontend as the primary MVP user channel.
- Telegram bot integration remains in codebase, but is no longer the default flow.
- Future delivery channels: Max / Bitrix.

## Expected Product Capabilities

- Import and process tickets and KB articles.
- Build/update RAG index from database data.
- Search by historical cases and KB.
- Rerank retrieved candidates before answer generation.
- Generate grounded answers for employees.
- Return citations and refuse answers when confidence is low.
- Help create, describe, and classify tickets.
- Escalate to human support when confidence is low.
- Accept text questions from the web frontend and proxy them to YandexGPT.
- Expose HTTP endpoints for health checks and chat requests used by the web UI.

## Infra / Run

- Python 3.11+
- Docker / docker compose for MSSQL restore and FastAPI service deploy
- Main local commands:
  - `uv sync`
  - `uv run python -m src.main`
  - `uv run pytest`
  - `uv run ruff check .`

## Important Files

- `README.md` — hackathon brief, requirements, DB setup.
- `.agents/AGENTS.md` — agent instructions for this repo.
- `.agents/index.md` — high-level architecture and important paths.
- `.agents/requirements.md` — compact feature list.
- `docs/database-analysis.md` — live MSSQL schema/content analysis and table map.
- `docs/tasks/` — source of truth for task workflow.
- `docker-compose.yml` — MSSQL and FastAPI service definitions for docker deploy.
- `Dockerfile` — container image for the FastAPI grounded RAG service.
- `.env.example` — environment variables template.
- `frontend/react-app/` — React MVP frontend for the question-answer flow.
- `README-frontend-web.md` — instructions for launching the web frontend.
- `src/api.py` — FastAPI app, endpoints, middleware, lifespan hooks.
- `src/services/yandex_gpt.py` — Yandex AI client for completion and embeddings.
- `src/services/telegram_bot.py` — Telegram long polling and grounded reply flow.
- `src/services/mssql_knowledge_base.py` — read-only MSSQL extraction and document building for tickets/KB.
- `src/services/qdrant_store.py` — Qdrant collection management, upsert and search.
- `src/services/rag_sync.py` — background sync from MSSQL to Qdrant with persisted state.
- `src/services/rag_pipeline.py` — retrieval, rerank, grounded answer generation and verification.
- `src/services/text_normalization.py` — HTML/XML cleanup, chunking and citation helpers.
- `src/config.py` — application settings from environment.
- `tests/test_api.py` / `tests/test_yandex_gpt.py` / `tests/test_rag_pipeline.py` — smoke/unit coverage for API, AI client and grounded pipeline.

## Maintenance Rule

- Update this file when major features, architecture, integrations, important files, or workflows change.
