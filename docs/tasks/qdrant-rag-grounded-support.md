# Task: Qdrant RAG Grounded Support

**Created:** 2026-04-18
**Status:** verify

---

## Design

### Problem
Нужно превратить текущий прокси к YandexGPT в support-ассистента, который отвечает только на основе MSSQL-базы сервис-деска: исторических тикетов и KB-статей. Ответ должен строиться через RAG на Qdrant, включать обязательные цитаты по источникам, проходить rerank и отдельную проверку на галлюцинации/уверенность.

### Why
Хакатон и будущий прод требуют полезного ассистента, который умеет доставать знания из 104k тикетов и 1k KB-документов, но при этом не придумывает факты. Для этого нужен не просто LLM-ответ, а управляемый retrieval pipeline с фильтрацией, доказательствами и безопасным отказом при низкой уверенности.

### Scope
- **In:** MSSQL read-only ingestion, нормализация HTML/XML, Qdrant-индекс, один тикет = один chunk, chunking KB, metadata-rich payload, retrieval, rerank, grounded answer generation, required citations, post-processing, confidence gating, API/Telegram integration, docs/tests.
- **Out:** админка, дашборд, тонкая бизнес-классификация заявок, полноценный UI, внешние источники знаний вне MSSQL.

## Invariants

- IV-1: Ассистент не должен использовать внешние знания в ответе; только контекст из MSSQL-источников, загруженных в индекс.
- IV-2: Каждый финальный ответ должен либо содержать проверяемые citations на найденные документы, либо явно отказываться отвечать из-за недостатка данных/уверенности.
- IV-3: Каждый тикет индексируется как один документ/chunk; KB-документы можно делить на chunks, если это нужно для качества retrieval.
- IV-4: KB является более надёжным источником для проверки правдивости; если KB не подтверждает ответ, итоговая уверенность должна снижаться.
- IV-5: При низкой уверенности, слабом retrieval или неподтверждённых фактах система должна отвечать, что не знает/не уверена, а не фантазировать.
- IV-6: Индекс должен строиться и обновляться из MSSQL в read-only режиме, без записи обратно в БД.

## Principles

- PC-1: Предпочесть безопасный отказ ложноположительному ответу.
- PC-2: Делать минимальную архитектуру, но с явными этапами: ingest -> index -> retrieve -> rerank -> answer -> verify.
- PC-3: Хранить максимум полезных metadata рядом с документом, чтобы retrieval и цитаты были объяснимыми.
- PC-4: Отделить ingest/sync от serving, чтобы решение можно было запускать локально и в docker.
- PC-5: Все неочевидные продуктовые допущения фиксировать в этом task-файле.

## Assumptions

- AS-1: Для retrieval будем использовать Qdrant как внешний vector store, а embeddings возьмём из Yandex AI Studio моделей `text-search-doc/latest` и `text-search-query/latest`.
- AS-2: Для rerank и для grounded verification достаточно YandexGPT в JSON-режиме; отдельный dedicated reranker model не обязателен для первого рабочего варианта.
- AS-3: Для тикетов лучший документ строится из `Task`, связанных `TaskExpenses`, lookup-справочников и нормализованных `TaskFieldValues`.
- AS-4: Для KB разумно делать chunking по длине после очистки HTML, потому что статьи часто очень длинные.
- AS-5: Для первого рабочего варианта периодический sync можно делать внутри процесса приложения с сохранением watermark/state локально.

## Unknowns

- UK-1: Какая длина KB chunk даст лучший баланс между recall и качеством цитирования без живой оценки на реальных запросах.
- UK-2: Потребуется ли позже более строгая доменная фильтрация по `Service`/`TaskType` для отсечения не-IT тикетов.
- UK-3: Хватит ли одного verifier pass или потребуется дополнительная rule-based валидация ответов под конкретные сценарии.

## TDD

Partial — интеграция большая, но критичные части пайплайна, API и confidence gating должны получить unit/API тесты с stub-клиентами.

---

## Plan

### Files

| File | Action | Description |
|------|--------|-------------|
| pyproject.toml | modify | Добавить зависимости для Qdrant и при необходимости для HTML cleanup |
| .env.example | modify | Добавить настройки MSSQL sync, Qdrant, embeddings, retrieval, thresholds |
| docker-compose.yml | modify | Поднять Qdrant рядом с API и MSSQL |
| Dockerfile | modify | Убедиться, что приложение и новые зависимости попадают в образ |
| README.md | modify | Описать RAG-архитектуру, запуск, sync и grounded-answer flow |
| README-fastapi-telegram.md | modify | Обновить описание API/Telegram под RAG вместо прямого прокси |
| .agents/index.md | modify | Обновить архитектурный индекс под ingestion/RAG/Qdrant |
| src/config.py | modify | Добавить конфиг RAG/Qdrant/MSSQL и thresholds |
| src/api.py | modify | Подключить RAG pipeline, новые response fields и health details |
| src/main.py | modify | Сохранить запуск FastAPI с новой инициализацией сервисов |
| src/services/yandex_gpt.py | modify | Добавить generic completion helpers и embeddings support |
| src/services/telegram_bot.py | modify | Перевести Telegram на grounded RAG ответы |
| src/services/rag_models.py | create | Общие dataclass/pydantic модели для документов, retrieval и answer verdict |
| src/services/text_normalization.py | create | Очистка HTML/XML, chunking KB и сборка citation/excerpt |
| src/services/mssql_knowledge_base.py | create | Read-only MSSQL extraction и нормализация тикетов/KB |
| src/services/qdrant_store.py | create | Работа с коллекцией, upsert/search и payload mapping |
| src/services/rag_sync.py | create | Первичная и периодическая синхронизация MSSQL -> Qdrant |
| src/services/rag_pipeline.py | create | Retrieval, rerank, answer generation, verification and final gating |
| tests/test_api.py | modify | Обновить API tests под structured grounded responses |
| tests/test_yandex_gpt.py | modify | Проверить embeddings/completion helpers и ошибки парсинга |
| tests/test_rag_pipeline.py | create | Проверить citation requirement, fallback и confidence rules |
| tests/test_text_normalization.py | create | Проверить HTML/XML cleanup и KB chunking |

### Interfaces

- `YandexGPTClient.generate_reply(...) -> str` сохраняется для простого completion.
- `YandexGPTClient.embed_text(text: str, kind: Literal["doc", "query"]) -> list[float]` возвращает embedding из Yandex AI Studio.
- `MSSQLKnowledgeBase.iter_documents(...) -> Iterator[RagDocument]` отдаёт нормализованные тикеты и KB chunks для индексации.
- `QdrantStore.upsert_documents(documents: Sequence[RagDocument]) -> None` и `search(...) -> list[RetrievedDocument]` управляют коллекцией.
- `RagSyncService.sync() -> SyncSummary` выполняет полную/инкрементальную синхронизацию.
- `RagPipeline.answer(question: str) -> GroundedAnswer` делает retrieve -> rerank -> answer -> verify -> confidence gate.

### Test Strategy

- Unit: нормализация HTML/XML, KB chunking, confidence scoring, citation validation.
- Service: RAG pipeline с fake retrieval/LLM проверить safe refusal и grounded success path.
- API: `/api/chat` должен возвращать structured grounded response и корректно обрабатывать upstream failures.

### Phases

1. **Phase 1**: Добавить конфиг, модели данных и утилиты нормализации.
2. **Phase 2**: Реализовать MSSQL extraction, Qdrant store и sync state.
3. **Phase 3**: Реализовать retrieval/rerank/answer/verify pipeline и подключить API/Telegram.
4. **Phase 4**: Обновить docs, docker, tests и провести verification.

### Dependencies

- Phase 2 depends on Phase 1.
- Phase 3 depends on Phase 2.
- Phase 4 depends on Phase 3.

---

## Execution

### Completed

- [x] Phase 1: Добавить конфиг, модели данных и утилиты нормализации.
- [x] Phase 2: Реализовать MSSQL extraction, Qdrant store и sync state.
- [x] Phase 3: Реализовать retrieval/rerank/answer/verify pipeline и подключить API/Telegram.
- [x] Phase 4: Обновить compose/env/index, тесты и провести verification.

### Decision Log

- D-1: Для первого рабочего варианта reranker будет реализован через YandexGPT listwise scoring в JSON-ответе. Это сохраняет требование «модели из Yandex AI Studio» и снимает риск привязки к неочевидному отдельному API/model URI без доступных локально кредов/документации.
- D-2: Для Qdrant 1.15 на VPS point ID переведены на детерминированный numeric hash, а исходный `ticket:<id>:<chunk>` сохраняется в payload.
- D-3: Для первичной загрузки с лимитами Yandex embeddings включены retry/backoff, последовательная подача embeddings и возобновление full sync по курсорам в state-файле.
- D-4: По запросу пользователя README-файлы не менялись; запрет на изменение `README*` без явного запроса добавлен в `.agents/AGENTS.md`.

---

## Verification

### Positive
- [x] Локально: `uv run pytest` -> 16 тестов прошли.
- [x] Локально: `uv run python -m compileall src tests` -> синтаксических ошибок нет.
- [x] Локально: `docker compose config` -> compose-конфигурация валидна.
- [x] VPS: изолированный контейнер `python:3.12-slim` выполнил `uv run pytest tests/test_api.py tests/test_rag_pipeline.py tests/test_yandex_gpt.py` -> 11 тестов прошли.
- [x] VPS: `docker compose up -d --build api` -> API-контейнер успешно пересобран и поднят.
- [x] VPS: `GET /health` -> API отвечает `status=ok`, `rag_enabled=true`, идёт фоновая индексация.
- [x] VPS: `POST /api/chat` на вопрос `Не подключается удаленка` -> сервис вернул безопасный отказ вместо выдуманного ответа.

### Negative
- [x] На VPS выявлен сбой подключения к MSSQL из контейнера из-за `localhost`; исправлено жёсткой docker-сетевой конфигурацией в compose.
- [x] На VPS выявлено расхождение схемы (`TaskTypeComboBox.NameXml` вместо ожидаемого `ValueXml`); SQL-запрос исправлен под реальную схему.
- [x] На VPS выявлены `429 Too Many Requests` от Yandex embeddings; добавлены retry/backoff, снижение параллелизма и resumable sync.
- [x] На VPS выявлена несовместимость строковых point ID с текущим Qdrant; переведено на numeric hash ID.

### Invariants
- [x] IV-1: Ответы строятся только через RAG-контекст из MSSQL -> при нехватке данных сервис отказывает.
- [x] IV-2: Финальный ответ либо содержит citations, либо возвращает явный отказ без цитат и с `needs_human=true`.
- [x] IV-3: Каждый тикет индексируется как один документ/chunk.
- [x] IV-4: Верификатор учитывает KB как более надёжный источник, а при сомнении снижает уверенность.
- [x] IV-5: При низкой уверенности `/api/chat` на VPS вернул честный отказ вместо галлюцинации.
- [x] IV-6: Синхронизация идёт из MSSQL только на чтение.

### Summary

Архитектура grounded RAG внедрена, тесты проходят локально и на VPS, API поднят на VPS и уже выполняет фоновую загрузку данных в Qdrant. На момент последней проверки `rag_indexed_documents=1050`, `rag_sync_running=true`: первичный full sync ещё продолжается, поэтому live-ответы пока могут чаще уходить в безопасный отказ.

---

## Review

### Invariant Checks

- [x] Архитектура соответствует цепочке ingest -> index -> retrieve -> rerank -> answer -> verify.
- [x] Главный риск сейчас не в корректности пайплайна, а в длительности первичного бэкфилла из-за объёма тикетов и лимитов embeddings API.

### Bug Findings

| # | Description | Severity | Confidence |
|---|-------------|----------|-------------|
| 1 | Первичный full sync по 104k тикетам на Yandex embeddings остаётся долгим даже после rate limiting fixes; до завершения бэкфилла полнота ответов на VPS ограничена. | medium | high |

### Recommendations

- После завершения первого бэкфилла повторно проверить типовые вопросы и качество rerank/citation на живых кейсах.
- При необходимости сократить датасет первичного индекса фильтрами по `Service`/`TaskType`, если полный корпус окажется слишком дорогим по embeddings.

---

## Conclusion

### What was done

- Добавлен полный grounded RAG-контур: MSSQL extraction, HTML/XML normalization, Qdrant indexing, rerank, answer generation, verifier, confidence gate.
- API и Telegram переведены с прямого вызова YandexGPT на RAG pipeline.
- Добавлены тесты для API, Yandex AI client, pipeline и нормализации.
- На VPS выполнены тесты, пересборка контейнера и live-smoke проверки.

### Assumptions verified

- AS-1: Подтверждено — embeddings `text-search-doc/latest` и `text-search-query/latest` работают на VPS и используются для реальной индексации.
- AS-2: Подтверждено частично — YandexGPT listwise rerank/verifier реализуемы, но скорость и качество ещё надо смотреть после полного бэкфилла.
- AS-3: Подтверждено — тикет успешно собирается из `Task`, `TaskExpenses`, `TaskFieldValues` и lookup-справочников.
- AS-4: Подтверждено — KB chunking готово к индексации.
- AS-5: Подтверждено — фоновый sync внутри процесса FastAPI работает и возобновляется по сохранённым курсорам.

### Lessons learned

- По живой MSSQL нельзя доверять только аналитическому документу: реальную схему нужно перепроверять на сервере.
- Для больших первичных индексов rate limiting embeddings нужно учитывать сразу, иначе full sync падает до первого полезного результата.

### Next steps

- Дождаться завершения первичного full sync на VPS и повторить smoke по типовым вопросам.
- При необходимости обновить Qdrant до версии ближе к клиентской, чтобы убрать compatibility warning.
