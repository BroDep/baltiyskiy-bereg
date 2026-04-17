# Baltiyskiy Bereg — Service Desk Chatbot

## Project Overview

Внутренний LLM-ассистент для сервис-деска «Балтийский Берег».
Source of truth — MSSQL с историческими тикетами и KB, целевая архитектура MVP — FastAPI + YandexGPT + Neo4j graph/vector knowledge store + Telegram polling worker.

**Проверенные факты окружения:**

- VPS доступен по SSH;
- MSSQL на VPS отвечает;
- подтверждённые объёмы данных: `Task = 104395`, `KBDocument = 1060`.

**Locked stack for MVP:** Python 3.11+, FastAPI, MSSQL, Neo4j 5, Docker, YandexGPT, aiogram.

---

## Repository Structure

```
baltiyskiy-bereg/
├── .agents/
│   ├── index.md
│   ├── AGENTS.md
│   ├── REQUIREMENTS.md
│   └── ROADMAP.md
├── src/
│   ├── api/
│   ├── database/
│   ├── models/
│   ├── services/
│   ├── settings/
│   ├── config.py
│   └── main.py
├── tests/
├── data/
├── .github/
├── Dockerfile
├── .dockerignore
├── docker-compose.yml
├── pyproject.toml
├── README.md
└── PRD.md
```

---

## Active MVP Architecture

| Component | Role |
|---|---|
| `api` | FastAPI backend, orchestration, admin settings endpoints |
| `mssql` | source database, read-only queries |
| `neo4j` | graph + vector knowledge store |
| `telegram-worker` | polling bot, общается только с API |
| `sync-worker` | scheduled sync из MSSQL/KB в Neo4j |
| `settings storage` | persistence для system prompt и LLM settings |
| `yandexgpt gateway` | request/response интеграция для `POST /api/llm/generate` |

---

## Data Sources

| Table | Purpose | Row Count |
|---|---|---|
| `Task` | сервис-деск тикеты | 104,395 |
| `KBDocument` | статьи базы знаний | 1,060 |
| `TaskFieldValues` | дополнительные поля тикетов | — |
| `TaskExpenses` | worklog / трудозатраты | — |
| `Service`, `TaskType`, `Priority`, `Status` | lookup-справочники | — |

---

## Delivery Rules

Каждая фича обязана идти через процесс:

`tests first -> implementation -> green tests -> review -> PR -> VPS smoke`

Это правило относится и к Docker/infra задачам, и к application feature work.

---

## CI/CD and VPS

### VPS

```
Host: 111.88.159.116
User: theimage01
SSH key: ~/.ssh/baltiyskiy_bereg_new
```

### Проверочные команды

```bash
ssh -i ~/.ssh/baltiyskiy_bereg_new theimage01@111.88.159.116
docker ps
docker logs api-baltbereg --tail=50
docker exec mssql-baltbereg /opt/mssql-tools/bin/sqlcmd \
  -S localhost -U SA -P "$MSSQL_SA_PASSWORD" \
  -Q 'SELECT COUNT(*) FROM service_desk_tdbb.dbo.Task'
```

---

## Key Documents

- `PRD.md` — целевое ТЗ MVP
- `.agents/REQUIREMENTS.md` — FR/NFR/AC
- `.agents/ROADMAP.md` — delivery plan

---

## Implemented API Surface

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/chat` | POST | текущий typed stub-контракт chat endpoint |
| `/api/llm/generate` | POST | минимальный YandexGPT request/response gateway |
| `/health` | GET | process/container healthcheck for Docker runtime |
| `/health/live` | GET | liveness probe |
| `/health/ready` | GET | readiness probe scaffold |

---

## Environment Variables

| Variable | Purpose |
|---|---|
| `MSSQL_HOST` / `MSSQL_PORT` / `MSSQL_DATABASE` / `MSSQL_USER` / `MSSQL_SA_PASSWORD` | read-only MSSQL connectivity |
| `YANDEX_GPT_API_KEY` | YandexGPT API key |
| `YANDEX_GPT_FOLDER_ID` | folder id for model URI |
| `YANDEX_GPT_MODEL` | default model name for runtime settings |
| `YANDEX_GPT_BASE_URL` | base URL for Yandex Foundation Models API |
| `SETTINGS_DATABASE_PATH` | SQLite file path for runtime settings storage |
| `DEFAULT_SYSTEM_PROMPT` | seeded system prompt value |
| `LLM_TEMPERATURE` | default temperature for persisted LLM settings |
| `LLM_MAX_TOKENS` | default max token limit |
| `LLM_TIMEOUT_SECONDS` | default upstream timeout |

---

## Known Blockers

- `superpowers` / skill loader сейчас падает с ошибкой `wasm-simd is not enabled`;
- текущий сервис в runtime был `unhealthy`, потому что healthcheck использовал `curl`, которого не было в image.
