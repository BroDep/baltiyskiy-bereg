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

## Known Blockers

- `superpowers` / skill loader сейчас падает с ошибкой `wasm-simd is not enabled`;
- текущий сервис в runtime был `unhealthy`, потому что healthcheck использовал `curl`, которого не было в image.
