# Task: FastAPI YandexGPT Telegram Bot

**Created:** 2026-04-18
**Status:** done

---

## Design

### Problem
Нужно собрать один сервер на FastAPI, который поднимает Telegram-бота, принимает сообщения от пользователя, отправляет их в YandexGPT и возвращает ответ обратно в Telegram.

### Why
Это даст рабочий прототип внешнего канала общения с LLM и базу для дальнейшей интеграции сервис-деска.

### Scope
- **In:** FastAPI-приложение, Telegram long polling в том же процессе, клиент YandexGPT, логирование, health endpoint, документация по запуску и переменным окружения.
- **Out:** RAG по MSSQL, webhook-развертывание, хранение истории диалога в БД, админка, сложная маршрутизация команд.

## Invariants

- IV-1: Текстовое сообщение из Telegram должно доходить до YandexGPT и ответ должен возвращаться в тот же чат.
- IV-2: Ошибки интеграций не должны падать молча; они логируются, а пользователю возвращается безопасное сообщение об ошибке.
- IV-3: Секреты читаются только из переменных окружения и не попадают в логи.
- IV-4: HTTP-сервер FastAPI должен иметь endpoint для проверки здоровья приложения.

## Principles

- PC-1: Выбрать минимальную и понятную архитектуру без лишних абстракций.
- PC-2: Использовать асинхронные библиотеки для сетевых интеграций.
- PC-3: Следовать существующему стилю проекта и держать изменения обратимыми.

## Assumptions

- AS-1: Для YandexGPT можно использовать native REST completion API с API-ключом и folder ID.
- AS-2: Для первого рабочего варианта достаточно Telegram long polling вместо webhook.
- AS-3: Одного процесса FastAPI + фонового Telegram polling достаточно для локального запуска и демо.

## Unknowns

- UK-1: Потребуется ли позже отдельное хранение истории сообщений для контекста между запросами.
- UK-2: Нужны ли дополнительные Telegram-команды кроме стартового приветствия и текстового диалога.

## TDD

No — задача интеграционная, но будут добавлены точечные тесты для конфигурации и вызова YandexGPT.

---

## Plan

### Files

| File | Action | Description |
|------|--------|-------------|
| pyproject.toml | modify | Добавить зависимости FastAPI, uvicorn, aiogram, httpx, pytest и инструменты для асинхронных тестов |
| .env.example | modify | Добавить переменные Telegram, YandexGPT, логирования и параметров приложения |
| README-fastapi-telegram.md | create | Вынести документацию по FastAPI/Telegram/YandexGPT в отдельный README-файл |
| Dockerfile | create | Собрать контейнер FastAPI + Telegram сервиса |
| .dockerignore | create | Исключить лишние файлы из docker build context |
| docker-compose.yml | modify | Поднять API-сервис и исправить запуск restore-db.sh в MSSQL контейнере |
| uv.lock | create | Зафиксировать lockfile после установки новых зависимостей |
| src/__init__.py | create | Сделать пакет приложения |
| src/config.py | create | Описать настройки приложения и чтение переменных окружения |
| src/logging_setup.py | create | Настроить общее логирование приложения и HTTP-запросов |
| src/services/__init__.py | create | Сделать пакет сервисов |
| src/services/yandex_gpt.py | create | Реализовать клиент YandexGPT через REST completion API |
| src/services/telegram_bot.py | create | Реализовать Telegram polling и проксирование сообщений в YandexGPT |
| src/api.py | create | Собрать FastAPI-приложение, endpoints и lifecycle-хуки |
| src/main.py | create | Точка входа для запуска uvicorn |
| tests/conftest.py | create | Добавить корень проекта в `sys.path` для тестов |
| tests/test_yandex_gpt.py | create | Проверить формирование/разбор ответов клиента YandexGPT |
| tests/test_api.py | create | Проверить health endpoint и HTTP chat endpoint |

### Interfaces

- `Settings` — валидирует конфиг из `.env` и собирает `model_uri` для YandexGPT (IV-3).
- `YandexGPTClient.generate_reply(message: str, system_prompt: str | None = None) -> str` — отправляет запрос в YandexGPT и возвращает текст ответа (IV-1, IV-2).
- `TelegramBotService.start() -> None` / `TelegramBotService.stop() -> None` — управляют polling внутри процесса FastAPI (IV-1, IV-4).
- `create_app(settings: Settings | None = None) -> FastAPI` — собирает HTTP API, middleware и lifecycle приложения (IV-4).

### Test Strategy

- Unit: проверить построение payload и разбор ответа YandexGPT-клиента.
- API: проверить `/health` и `/api/chat` через FastAPI TestClient/ASGI transport.
- Smoke: импорт приложения, запуск тестов, проверка, что Telegram сервис можно отключить в тестовом окружении.

### Phases

1. **Phase 1**: Подготовить структуру проекта, зависимости и конфигурацию.
2. **Phase 2**: Реализовать YandexGPT-клиент, FastAPI API и Telegram polling.
3. **Phase 3**: Подключить логирование, документацию и автоматические проверки.

### Dependencies

- Phase 2 depends on Phase 1.
- Phase 3 depends on Phase 2.

---

## Execution

### Completed

- [x] Phase 1: Подготовить структуру проекта, зависимости и конфигурацию.
- [x] Phase 2: Реализовать YandexGPT-клиент, FastAPI API и Telegram polling.
- [x] Phase 3: Подключить логирование, документацию и автоматические проверки.

---

## Verification

### Positive
- [x] `python -m compileall src tests` — исходники и тесты успешно скомпилировались без синтаксических ошибок.
- [x] `uv run pytest` — 5 тестов прошли успешно.
- [x] `uv run python - <<...` smoke check — `GET /health` вернул `{"status": "ok", "telegram_bot_enabled": false}` при отключенном Telegram-боте.
- [x] `docker compose config` — docker-конфигурация валидируется локально.
- [x] `docker build -t baltiyskiy-bereg-api:test .` — контейнер FastAPI-сервиса успешно собран локально.

### Negative
- [x] Тест `test_chat_endpoint_returns_502_on_yandex_error` подтвердил контролируемый ответ `502` при ошибке upstream.
- [x] Тест `test_generate_reply_raises_on_invalid_response` подтвердил обработку невалидного ответа YandexGPT.

### Invariants
- [x] IV-1: В `TelegramBotService` текстовые сообщения отправляются в `YandexGPTClient.generate_reply`, а ответ возвращается в тот же чат.
- [x] IV-2: Ошибки upstream логируются; Telegram получает fallback-текст, HTTP API — `502`.
- [x] IV-3: Секреты читаются из настроек окружения, в логах фиксируются только статусы, ID и длины сообщений.
- [x] IV-4: FastAPI-приложение поднимает `/health`, smoke check выполнен успешно.

### Summary

Реализован единый FastAPI-сервер с Telegram long polling, клиентом YandexGPT, HTTP API, базовым логированием и docker-конфигурацией для VPS. Автотесты и smoke check пройдены.

---

## Review

### Invariant Checks

- [x] IV-1: PASS — поток Telegram → YandexGPT → Telegram реализован.
- [x] IV-2: PASS — предусмотрены логирование и безопасные ответы при сбоях.
- [x] IV-3: PASS — секреты не выводятся в логи и читаются только из env.
- [x] IV-4: PASS — health endpoint присутствует и проверен.

### Bug Findings

| # | Description | Severity | Confidence |
|---|-------------|----------|-------------|
| — | Блокирующих проблем по итогам self-review не найдено | — | — |

### Recommendations

- Добавить webhook-режим для продакшн-развертывания.
- Добавить хранение истории диалога и RAG по MSSQL/KB в следующей задаче.

---

## Conclusion

### What was done

- Добавлен пакет `src/` с конфигурацией, FastAPI API, логированием и сервисами YandexGPT/Telegram.
- Добавлены тесты для HTTP API и клиента YandexGPT.
- Добавлены `Dockerfile` и обновлен `docker-compose.yml` для запуска API на VPS.
- Обновлены `.env.example`, `README-fastapi-telegram.md`, `.agents/index.md` и task file.

### Assumptions verified

- AS-1: Подтверждено — использован native REST completion API YandexGPT с `modelUri` и `Authorization: Api-Key`.
- AS-2: Подтверждено — Telegram long polling встроен в lifecycle FastAPI.
- AS-3: Подтверждено локально — приложение и проверки работают в одном процессе при отключаемом Telegram в тестах.

### Lessons learned

- Для стабильных тестов важно явно переопределять env-зависимые настройки и отключать Telegram polling.

### Next steps

- Заполнить реальные `YANDEX_GPT_*` и `TELEGRAM_BOT_TOKEN` в `.env` и проверить end-to-end переписку с ботом.
- При необходимости добавить webhook, хранение контекста и интеграцию с MSSQL/RAG.
