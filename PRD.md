# Baltiyskiy Bereg — MVP PRD / ТЗ

## 1. Цель

Построить MVP ассистента сервис-деска, который:

- отвечает сотрудникам на русском языке;
- использует историю тикетов и KB как основание ответа;
- не пишет в source MSSQL, а читает его только в read-only режиме;
- может быть вызван как из веб/API, так и из Telegram;
- управляется через dashboard-настройки системного промпта и параметров LLM.

## 2. Что входит в MVP

### In scope

1. FastAPI-сервис с простым YandexGPT request/response endpoint.
2. Chat endpoint c server-side tool orchestration.
3. Telegram bot через polling.
4. Два dashboard endpoint'а:
   - управление системным промптом;
   - управление LLM settings.
5. Graph+vector knowledge store.
6. Scheduled sync из MSSQL и KB в knowledge store.
7. Health/live/ready checks и VPS smoke verification.
8. TDD-first delivery process и обязательный review gate.

### Out of scope на MVP-этапе

- auth для dashboard;
- Bitrix24 и Max;
- полноценная admin-панель с RBAC;
- продвинутый классификатор заявок как отдельный ML-модуль;
- real-time CDC из MSSQL.

## 3. Архитектурные решения

| Область | Решение | Почему |
|---|---|---|
| API | FastAPI | простой async backend и нормальный OpenAPI |
| LLM | YandexGPT | основное требование проекта |
| Telegram | `aiogram` polling worker | не нужен публичный webhook, проще для VPS MVP |
| Source DB | MSSQL read-only | source of truth уже существует |
| Knowledge store | Neo4j 5 + vector/fulltext indexes | один стек под graph relations и vector retrieval |
| Runtime settings | SQLite | без отдельного infra, но с нормальной персистентностью |
| Tool access | server-side orchestration | контролируемый и тестируемый доступ к данным |

## 4. Целевая архитектура

### 4.1 Компоненты

1. **api** — FastAPI приложение.
2. **telegram-worker** — polling бот, который шлёт запросы в API.
3. **mssql** — источник данных, только чтение.
4. **neo4j** — graph+vector knowledge store.
5. **sync-worker** — scheduled job, который обновляет knowledge graph.
6. **settings storage** — SQLite для системного промпта и LLM настроек.

### 4.2 Поток данных

#### Sync pipeline

`MSSQL/KB -> extractor -> normalizer -> embeddings -> Neo4j nodes/relations/vector indexes`

#### Chat pipeline

`User -> API/Telegram -> chat orchestrator -> tools(graph search / neighbor expansion / article fetch) -> YandexGPT -> response`

## 5. API scope

### 5.1 Simple LLM gateway

`POST /api/llm/generate`

Назначение: минимальный request/response endpoint к YandexGPT для smoke и интеграций.

### 5.2 Chat endpoint

`POST /api/chat`

Назначение: основной endpoint, который:

1. нормализует запрос;
2. вызывает retrieval tools;
3. формирует контекст;
4. обращается в YandexGPT;
5. возвращает ответ и источники.

### 5.3 Dashboard settings endpoints

- `GET /api/admin/system-prompt`
- `PUT /api/admin/system-prompt`
- `GET /api/admin/llm-settings`
- `PUT /api/admin/llm-settings`

### 5.4 Health endpoints

- `GET /health/live`
- `GET /health/ready`

## 6. Knowledge graph design

### 6.1 Основные сущности

- `Ticket`
- `TicketMessage`
- `KBArticle`
- `KBChunk`
- `Service`
- `TaskType`
- `Priority`
- `Status`

### 6.2 Основные связи

- `(:Ticket)-[:HAS_MESSAGE]->(:TicketMessage)`
- `(:Ticket)-[:BELONGS_TO_SERVICE]->(:Service)`
- `(:Ticket)-[:HAS_TYPE]->(:TaskType)`
- `(:Ticket)-[:HAS_PRIORITY]->(:Priority)`
- `(:Ticket)-[:HAS_STATUS]->(:Status)`
- `(:KBArticle)-[:HAS_CHUNK]->(:KBChunk)`
- `(:KBChunk)-[:RELATED_TO_SERVICE]->(:Service)`

### 6.3 Retrieval strategy

1. fulltext lookup по ключевым словам и точным терминам;
2. vector similarity по embedding;
3. graph expansion по связанным сущностям;
4. сбор финального context package для LLM.

## 7. Scheduled sync

### MVP режим

- nightly full sync;
- manual reindex command;
- dry-run mode для безопасной отладки;
- идемпотентная загрузка по source identifiers.

### Первичный охват данных

- `Task`
- `TaskFieldValues`
- `TaskExpenses`
- `KBDocument`
- lookup-таблицы (`Service`, `TaskType`, `Priority`, `Status`)

## 8. Telegram MVP

### Решение

- отдельный polling worker;
- worker не имеет прямого доступа к MSSQL/Neo4j;
- worker ходит только в FastAPI endpoint'ы;
- transport layer отделён от knowledge / orchestration logic.

### Базовые команды

- `/start`
- `/help`
- свободный текст -> `/api/chat`

## 9. Dashboard MVP

Dashboard на MVP уровне — это сначала API, затем UI.

### Обязательно

- просмотр текущего system prompt;
- обновление system prompt;
- просмотр LLM settings;
- обновление LLM settings;
- сохранение значений между рестартами.

### Необязательно в первом срезе

- история изменений;
- rollback;
- роли/разграничение доступа.

## 10. Engineering workflow — обязательный

Для каждой задачи команда обязана соблюдать один и тот же delivery pipeline:

1. сформулировать acceptance criteria;
2. сначала написать тесты / контрактные проверки;
3. убедиться, что тесты падают ожидаемо;
4. написать минимальный код;
5. прогнать локально все тесты;
6. только после зелёного прогона запрашивать review;
7. только после review открывать PR;
8. после merge в `dev` выполнять smoke на VPS.

Нарушение этого процесса считается незавершённой поставкой.

## 11. Acceptance criteria верхнего уровня

1. API контейнер собирается и проходит healthcheck.
2. MSSQL и VPS доступны и проверяются smoke-командами.
3. `/api/llm/generate` возвращает ответ от YandexGPT.
4. Telegram polling worker принимает сообщение и получает ответ от API.
5. Dashboard endpoints сохраняют и отдают настройки.
6. Scheduled sync создаёт узлы/связи/векторные индексы в Neo4j.
7. `/api/chat` использует retrieval tools до ответа пользователю.
8. Каждый delivery issue содержит TDD gate и VPS smoke gate.

## 12. Риски

- `superpowers/skill loader` сейчас падает с ошибкой `wasm-simd is not enabled`;
- source HTML в `Task.Comment` может быть грязным и неоднородным;
- vector search quality зависит от выбранных embeddings и схемы чанкинга;
- отсутствие auth на dashboard допустимо только для внутреннего MVP стенда.
