# Project Index

## Project

- Baltiyskiy Bereg service desk assistant.
- Goal: help employees ask questions, describe incidents, and get solution hints from historical tickets and KB articles.

## Core Data Sources

- MSSQL database `service_desk_tdbb`.
- Main tables: `Task`, `TaskFieldValues`, `TaskExpenses`, `KBDocument`.

## Main Integrations

- MSSQL as read-only source of tickets and KB.
- YandexGPT as LLM provider.
- Telegram bot integrated into the FastAPI process via long polling.
- Future delivery channels: Max / Bitrix.

## Expected Product Capabilities

- Import and process tickets and KB articles.
- Build/update RAG index from database data.
- Search by historical cases and KB.
- Generate grounded answers for employees.
- Help create, describe, and classify tickets.
- Escalate to human support when confidence is low.
- Accept text messages from Telegram and proxy them to YandexGPT.
- Expose HTTP endpoints for health checks and direct chat testing.

## Infra / Run

- Python 3.11+
- Docker / docker compose for MSSQL restore and local infra
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
- `docs/tasks/` — source of truth for task workflow.
- `docker-compose.yml` — local MSSQL setup.
- `.env.example` — environment variables template.
- `src/api.py` — FastAPI app, endpoints, middleware, lifespan hooks.
- `src/services/yandex_gpt.py` — YandexGPT client over REST completion API.
- `src/services/telegram_bot.py` — Telegram long polling and reply flow.
- `src/config.py` — application settings from environment.
- `tests/test_api.py` / `tests/test_yandex_gpt.py` — smoke/unit coverage for API and LLM client.

## Maintenance Rule

- Update this file when major features, architecture, integrations, important files, or workflows change.
