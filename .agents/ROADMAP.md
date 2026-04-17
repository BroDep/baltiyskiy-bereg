# Roadmap — Baltiyskiy Bereg MVP

## Delivery Principles

Для **каждой** задачи действует одинаковый pipeline:

1. acceptance criteria;
2. tests first;
3. minimal implementation;
4. all relevant tests green;
5. reviewer / code review;
6. PR в `dev`;
7. VPS smoke verification.

Задача без этих шагов считается незавершённой.

---

## Phase 0 — Foundation and Tooling

### R-001. Docker / runtime foundation — GitHub issue #11
- multi-stage Dockerfile;
- `.dockerignore`;
- рабочий container healthcheck без `curl`;
- smoke сборка локально и на VPS.

**DoD:** контейнер API собирается и перестаёт быть `unhealthy` из-за runtime image.

### R-002. Superpowers / agent tooling recovery — GitHub issue #24
- зафиксировать и починить `skill loader` / `wasm-simd` blocker;
- документировать fallback-процесс, если инструмент недоступен.

**DoD:** агентные workflow либо работают, либо имеют формально описанный обходной путь.

### R-003. CI / TDD / review gates — GitHub issue #23
- убрать ложнозелёные проверки;
- зафиксировать pipeline `tests -> code -> green -> review -> PR -> VPS smoke`;
- встроить это в backlog и PR правила.

**DoD:** ветка не считается готовой без зелёного quality gate.

---

## Phase 1 — Backend Skeleton

### R-010. Application skeleton and config — GitHub issue #12
- нормальная структура `src/`;
- config/settings layer;
- settings persistence для dashboard;
- заготовка readiness/liveness.

**DoD:** проект не является single-file stub и готов к расширению по слоям.

### R-011. MSSQL read model and readiness — GitHub issue #14
- read-only клиент для MSSQL;
- базовые smoke запросы;
- readiness checks на соединение.

**DoD:** API умеет честно говорить, видит ли он source DB.

---

## Phase 2 — LLM Access and Dashboard API

### R-020. YandexGPT request-response endpoint — GitHub issue #13
- `POST /api/llm/generate`;
- timeout / error handling;
- mocked/integration tests.

**DoD:** можно отправить prompt и получить ответ от YandexGPT через сервис.

### R-021. Dashboard settings API — GitHub issue #19
- `GET/PUT /api/admin/system-prompt`;
- `GET/PUT /api/admin/llm-settings`;
- сохранение между рестартами;
- без auth на MVP-стенде.

**DoD:** фронт/дашборд может читать и менять runtime настройки.

---

## Phase 3 — Knowledge Graph Platform

### R-030. Neo4j graph+vector foundation — GitHub issue #15
- docker/service setup для Neo4j;
- schema, labels, relations;
- vector + fulltext indexes.

**DoD:** knowledge store поднят и готов принимать данные.

### R-031. Scheduled sync from MSSQL/KB — GitHub issue #16
- extractor / normalizer;
- batch sync в Neo4j;
- nightly schedule + manual run;
- идемпотентность.

**DoD:** source данные переносятся в graph/vector слой воспроизводимо.

---

## Phase 4 — Tool-enabled Assistant

### R-040. Chat orchestration with tools — GitHub issue #17
- `POST /api/chat`;
- tool contracts для graph lookup;
- сбор источников и context package;
- ответ + citations / metadata.

**DoD:** ответ строится не вслепую, а через retrieval tools.

### R-041. Telegram polling worker — GitHub issue #18
- `aiogram` polling worker;
- вызов FastAPI вместо прямого доступа к данным;
- retry / timeout / basic command set.

**DoD:** Telegram пользователь получает ответ от backend pipeline.

---

## Phase 5 — Operations and Demo Readiness

### R-050. Dashboard UI — GitHub issue #20
- UI для system prompt;
- UI для LLM settings;
- минимум operational visibility для demo.

**DoD:** настройки можно менять без ручного редактирования файлов/БД.

### R-051. VPS smoke and release checklist — GitHub issue #23
- post-merge smoke сценарий;
- проверка API, DB, sync, Telegram worker;
- фиксация результатов в PR/release notes.

**DoD:** есть повторяемый способ доказать, что система жива на VPS.

---

## Priority Order

1. R-001
2. R-002
3. R-003
4. R-010
5. R-011
6. R-020
7. R-021
8. R-030
9. R-031
10. R-040
11. R-041
12. R-050
13. R-051

---

## Stack Decisions Locked for MVP

- **API:** FastAPI
- **Telegram:** aiogram polling worker
- **LLM:** YandexGPT
- **Source DB:** MSSQL read-only
- **Knowledge store:** Neo4j 5 with vector and fulltext indexes
- **Settings store:** SQLite
