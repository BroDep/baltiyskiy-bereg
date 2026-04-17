# Requirements — Baltiyskiy Bereg MVP

## 1. Product Goal

Сервис должен помогать сотрудникам быстро получать ответы по IT-вопросам, используя исторические тикеты и KB, а также обеспечивать безопасную эволюцию в сторону tool-enabled assistant'а.

## 2. Scope

### In Scope

- FastAPI backend;
- доступ к YandexGPT;
- Telegram polling worker;
- dashboard settings API без auth на MVP;
- Neo4j knowledge store с graph+vector индексами;
- scheduled sync из MSSQL и KB;
- chat orchestration через инструменты retrieval;
- обязательные TDD / review / VPS smoke quality gates.

### Out of Scope

- dashboard auth и RBAC;
- Bitrix24 / Max интеграции;
- продвинутый ML classifier как обязательная часть MVP;
- real-time replication из MSSQL.

## 3. Architecture Constraints

| ID | Constraint |
|---|---|
| **AR-001** | MSSQL используется только в read-only сценарии. |
| **AR-002** | Telegram worker не ходит в БД напрямую, только в API. |
| **AR-003** | Graph и vector слой реализуется через Neo4j 5. |
| **AR-004** | Runtime prompt/settings не хранятся в Neo4j; для них используется отдельное settings storage. |
| **AR-005** | LLM не получает прямой доступ к БД; все tool calls исполняет backend. |

## 4. Functional Requirements

| ID | Requirement |
|---|---|
| **FR-001** | Сервис MUST предоставлять FastAPI endpoint `POST /api/llm/generate` для базового request/response вызова YandexGPT. |
| **FR-002** | Сервис MUST хранить и отдавать системный промпт через `GET/PUT /api/admin/system-prompt`. |
| **FR-003** | Сервис MUST хранить и отдавать LLM runtime settings через `GET/PUT /api/admin/llm-settings`. |
| **FR-004** | Сервис MUST поднимать Telegram polling worker, который пересылает пользовательские сообщения в FastAPI. |
| **FR-005** | Сервис MUST строить knowledge graph из `Task`, `TaskFieldValues`, `TaskExpenses`, `KBDocument` и lookup-таблиц. |
| **FR-006** | Сервис MUST выполнять scheduled sync из MSSQL/KB в Neo4j в идемпотентном режиме. |
| **FR-007** | Сервис MUST предоставлять `POST /api/chat`, который до генерации вызывает retrieval tools для получения контекста из Neo4j. |
| **FR-008** | Сервис MUST возвращать источники / metadata в ответе chat endpoint. |
| **FR-009** | Сервис MUST иметь `GET /health/live` и `GET /health/ready` для различения liveness и readiness. |
| **FR-010** | Сервис SHOULD поддерживать manual reindex / resync для knowledge graph. |
| **FR-011** | Сервис SHOULD сохранять dashboard settings между рестартами. |

## 5. Non-Functional Requirements

### Performance

| ID | Requirement |
|---|---|
| **NFR-001** | `POST /api/llm/generate` SHOULD отвечать менее чем за 30 секунд. |
| **NFR-002** | `POST /api/chat` SHOULD отвечать менее чем за 30 секунд при штатной нагрузке MVP. |
| **NFR-003** | Scheduled sync MAY выполняться batch-режимом; near real-time не требуется. |

### Reliability

| ID | Requirement |
|---|---|
| **NFR-010** | API контейнер MUST считаться healthy без зависимости от внешнего `curl` в runtime image. |
| **NFR-011** | Readiness check MUST валидировать критические зависимости: как минимум API process, затем по фазам MSSQL / YandexGPT / Neo4j. |
| **NFR-012** | Sync job MUST быть идемпотентным и повторяемым. |

### Security

| ID | Requirement |
|---|---|
| **NFR-020** | Secrets MUST храниться только в `.env` / GitHub secrets и не коммититься в git. |
| **NFR-021** | Dashboard без auth допускается только для внутреннего MVP стенда. |
| **NFR-022** | Прямой write-back в MSSQL запрещён. |

### Observability

| ID | Requirement |
|---|---|
| **NFR-030** | Компоненты MUST логировать ошибки YandexGPT, Neo4j, MSSQL и sync pipeline. |
| **NFR-031** | VPS smoke check MUST быть частью delivery процесса после merge в `dev`. |

## 6. Delivery Process Requirements

| ID | Requirement |
|---|---|
| **DPR-001** | Для каждой задачи команда MUST сначала написать тесты или контрактные проверки. |
| **DPR-002** | Реализация MUST начинаться только после появления failing checks. |
| **DPR-003** | Перед review MUST быть зелёный локальный прогон релевантных тестов. |
| **DPR-004** | Перед PR MUST быть выполнен self-check по acceptance criteria. |
| **DPR-005** | После merge в `dev` MUST быть выполнен VPS smoke/manual verification. |
| **DPR-006** | Если `superpowers` tooling недоступен, это MUST фиксироваться как явный блокер/issue, а не игнорироваться. |

## 7. Acceptance Criteria Matrix

| ID | Criterion | Verification |
|---|---|---|
| **AC-001** | Docker image собирается через multi-stage + `uv sync`. | `docker build .` |
| **AC-002** | API healthcheck проходит без `curl` внутри контейнера. | `docker inspect ... State.Health` |
| **AC-003** | VPS доступен по SSH, MSSQL отвечает на smoke query. | SSH + `sqlcmd SELECT COUNT(*)` |
| **AC-004** | `POST /api/llm/generate` возвращает ответ от YandexGPT. | integration / mocked test |
| **AC-005** | `GET/PUT /api/admin/system-prompt` сохраняет и отдаёт состояние. | API tests |
| **AC-006** | `GET/PUT /api/admin/llm-settings` сохраняет и отдаёт состояние. | API tests |
| **AC-007** | Scheduled sync создаёт/обновляет графовые сущности в Neo4j. | sync integration test |
| **AC-008** | `POST /api/chat` вызывает retrieval tools до генерации ответа. | orchestration tests + logs |
| **AC-009** | Telegram polling worker получает сообщение и возвращает ответ через API. | integration / smoke test |
| **AC-010** | Каждый roadmap issue содержит TDD gate, review gate и VPS smoke gate. | manual backlog audit |

## 8. Source Data

| Table | Purpose |
|---|---|
| `Task` | исторические тикеты и описания проблем |
| `TaskFieldValues` | дополнительные атрибуты тикетов |
| `TaskExpenses` | служебные комментарии и worklog |
| `KBDocument` | KB статьи |
| `Service`, `TaskType`, `Priority`, `Status` | классификационные сущности |

## 9. Delivery Priority

1. Docker/runtime health.
2. FastAPI + config skeleton.
3. YandexGPT request/response endpoint.
4. Dashboard settings API.
5. Neo4j graph/vector foundation.
6. Scheduled sync.
7. Tool-enabled chat.
8. Telegram polling.
