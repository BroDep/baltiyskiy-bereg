# Baltiyskiy Bereg — Service Desk AI Assistant

LLM-чатбот для сервис-деска «Балтийский Берег». Цель MVP — отвечать на вопросы сотрудников на основе MSSQL-истории тикетов и базы знаний, использовать YandexGPT для генерации и Neo4j как graph+vector knowledge store.

## Текущий статус

- репозиторий пока находится в стадии foundation / starter;
- VPS доступен по SSH;
- MSSQL на VPS проверен: `Task = 104395`, `KBDocument = 1060`;
- текущий backend теперь реализует контрактный FastAPI skeleton для `/api/chat`, `/health/live` и `/health/ready`;
- целевая архитектура и backlog теперь описаны в `PRD.md`, `.agents/REQUIREMENTS.md`, `.agents/ROADMAP.md`.

## Целевой MVP

1. **FastAPI backend** с доступом к YandexGPT в формате request → response.
2. **Telegram bot на polling**, который общается с FastAPI, а не с БД напрямую.
3. **Dashboard API** для управления системным промптом и LLM-настройками без auth на MVP-этапе.
4. **Scheduled sync** из MSSQL/KB в graph+vector knowledge store.
5. **Tool-enabled chat orchestration**: перед финальным ответом LLM уточняет контекст через контролируемые инструменты поиска в knowledge store.

## Архитектурные решения

| Область | Решение |
|---|---|
| Web API | FastAPI |
| LLM | YandexGPT |
| Source of truth | MSSQL (read-only) |
| Graph + vector store | Neo4j 5 + vector/fulltext indexes |
| Telegram transport | Polling worker на `aiogram` |
| Runtime settings | SQLite / локальное settings storage для dashboard |
| Orchestration | Server-side tool loop, а не прямой доступ LLM к БД |

## Документы проекта

- `PRD.md` — нормализованное ТЗ / продуктовая и техническая рамка MVP.
- `.agents/REQUIREMENTS.md` — формализованные FR/NFR/AC.
- `.agents/ROADMAP.md` — поэтапный delivery plan и quality gates.
- `.agents/AGENTS.md` — правила для AI-агентов.

## Текущие endpoints

### Реально реализованы сейчас

| Endpoint | Method | Назначение |
|---|---|---|
| `/` | GET | stub-ответ сервиса |
| `/api/chat` | POST | typed chat contract with deterministic stub response and controlled failure shape |
| `/health/live` | GET | process liveness |
| `/health/ready` | GET | readiness based on internal dependency probe abstraction |

### Запланированы в MVP

| Endpoint | Method | Назначение |
|---|---|---|
| `/api/llm/generate` | POST | простой запрос к YandexGPT |
| `/api/admin/system-prompt` | GET / PUT | чтение и обновление системного промпта |
| `/api/admin/llm-settings` | GET / PUT | чтение и обновление runtime LLM settings |

## Contract notes for `/api/chat`

- request body requires `message` and may include `correlation_id`, `user_id`, and `source`;
- success response keeps a stable plain-text shape: `status=ok`, `response_text`, `correlation_id`;
- controlled failure currently uses the sentinel message `__force_chat_failure__` and returns `503` with `status=error`, `error_code=CHAT_UNAVAILABLE`, a short user-facing message, and `correlation_id`;
- readiness degradation returns `503` with a dependency summary and no stack traces.

## Быстрый старт

```bash
uv sync --dev
uv run pytest tests/test_api_contract.py
uv run uvicorn src.main:app --reload
uv run python -m src.telegram_worker.main
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

## Telegram worker

Минимальный polling worker запускается отдельно от FastAPI и общается только с `/api/chat`:

```bash
export TELEGRAM_BOT_TOKEN=0000000000:replace-me
export BACKEND_API_BASE_URL=http://localhost:8000
export API_TIMEOUT_SECONDS=15

uv run python -m src.telegram_worker.main
```

Для Docker Compose:

```bash
docker compose up -d api telegram-worker
docker compose logs -f telegram-worker
```

## Docker

Используется multi-stage build с `uv sync` и уменьшенным build context через `.dockerignore`.
Healthcheck API не зависит от `curl` внутри контейнера и выполняется через встроенный Python runtime.

## Verification

```bash
pytest tests/test_api_contract.py
python -m pytest tests/test_api_contract.py -q
uv run pytest tests/test_telegram_worker.py
```

## Правило разработки

Для каждой фичи workflow обязателен:

1. сначала тесты / контракт / acceptance criteria;
2. потом минимальная реализация;
3. потом локально все тесты зелёные;
4. потом code review / reviewer;
5. потом PR в `dev`;
6. потом smoke / manual verification на VPS.

## Ссылки

- GitHub: https://github.com/BroDep/baltiyskiy-bereg
- VPS: `111.88.159.116`
- Платформа: https://app.ai-business-spb.ru
