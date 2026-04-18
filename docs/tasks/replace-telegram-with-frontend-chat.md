# Task: Replace Telegram With Frontend Chat

**Created:** 2026-04-18
**Status:** execute

---

## Design

### Problem
Нужно заменить Telegram как основной пользовательский канал на веб-фронтенд и дать пользователю простой интерфейс вопрос-ответ для работы с текущим FastAPI + YandexGPT backend.

### Why
Веб-интерфейс проще тестировать и показывать на демо, а текущая Telegram-интеграция зависит от внешней сетевой доступности к Telegram API, что уже стало блокером на VPS.

### Scope
- **In:** простой React-фронтенд на основе структуры из `origin/feature/rag-backend-frontend`, экран чата вопрос-ответ, проверка здоровья backend, адаптация FastAPI под `/api/health`, документация запуска фронтенда, безопасное отключение Telegram по умолчанию, сборка фронтенда в Docker image для запуска на VPS.
- **Out:** авторизация, история чатов, аналитика, список тикетов, полноценный RAG UI, миграция старой Telegram-логики на удаление.

## Invariants

- IV-1: Пользователь может открыть фронтенд, отправить текстовый вопрос и получить текстовый ответ от backend.
- IV-2: Frontend явно показывает состояние backend (доступен/недоступен) и состояние отправки сообщения.
- IV-3: Текущий backend API `/api/chat` продолжает работать для простой схемы вопрос-ответ.
- IV-4: Telegram-код не удаляется, но по умолчанию не мешает новому web-flow.

## Principles

- PC-1: Выбрать минимальный MVP-интерфейс без лишней бизнес-логики.
- PC-2: Брать за основу структуру фронтенда из `origin/feature/rag-backend-frontend`, а не изобретать новую иерархию.
- PC-3: Все неочевидные допущения фиксировать явно; для этой задачи по умолчанию реализуется только простой chat flow.

## Assumptions

- AS-1: Под «вместо телеграма делаем фронтенд» в рамках этой задачи нужен MVP question-answer интерфейс, а не вся расширенная матрица `/api/auth`, `/api/chat/history`, `/api/analytics/*`.
- AS-2: Для первого шага достаточно MVP фронтенда без auth/history/analytics, но его нужно уметь собирать и отдавать через текущий docker deploy на VPS.
- AS-3: Совместимости по данным достаточно на уровне существующего ответа `{ reply: string }` от `/api/chat`.

## Unknowns

- UK-1: Нужен ли в следующем шаге полный контракт из таблицы endpoints (auth/history/analytics).
- UK-2: Нужна ли позже отдельная frontend-инфраструктура вместо текущего встроенного FastAPI-serving.

## TDD

No — для MVP приоритет у быстрой интеграции UI + API, но будут добавлены backend-regression проверки и проверка сборки фронтенда.

---

## Plan

### Files

| File | Action | Description |
|------|--------|-------------|
| pyproject.toml | modify | При необходимости добавить backend-зависимости для frontend-serving/CORS, если это понадобится для MVP |
| .env.example | modify | Сместить дефолт в сторону frontend-flow и зафиксировать frontend env-переменные |
| src/config.py | modify | Отключить Telegram по умолчанию и добавить frontend-related настройки при необходимости |
| src/api.py | modify | Добавить `/api/health`, сохранить `/api/chat` и научить FastAPI отдавать built frontend |
| tests/test_api.py | modify | Добавить проверки для frontend-friendly health/chat сценариев |
| .gitignore | modify | Исключить `node_modules` и локальные frontend артефакты |
| .dockerignore | modify | Исключить frontend build/node_modules из docker context |
| Dockerfile | modify | Собирать React frontend в отдельном stage и копировать build в Python image |
| frontend/react-app/package.json | create | Добавить React frontend package на основе ветки `feature/rag-backend-frontend` |
| frontend/react-app/package-lock.json | create | Зафиксировать npm lockfile для воспроизводимой сборки |
| frontend/react-app/public/index.html | create | Создать HTML entrypoint приложения |
| frontend/react-app/src/index.js | create | Точка входа React-приложения |
| frontend/react-app/src/index.css | create | Базовые стили для chat UI |
| frontend/react-app/src/App.jsx | create | Корневой компонент, загрузка health и отправка сообщений |
| frontend/react-app/src/components/ChatWindow.jsx | create | Контейнер истории сообщений и loading state |
| frontend/react-app/src/components/Message.jsx | create | Отображение bubble для user/assistant сообщения |
| frontend/react-app/src/components/MessageInput.jsx | create | Поле ввода и отправка сообщений |
| frontend/react-app/src/components/ConfidenceBadge.jsx | create | Совместимый placeholder для будущих confidence метаданных |
| frontend/react-app/src/components/SourceList.jsx | create | Совместимый placeholder для будущих source метаданных |
| README-frontend-web.md | create | Документация по запуску frontend question-answer режима |
| .agents/index.md | modify | Обновить карту проекта под новый web channel |

### Interfaces

- `GET /api/health -> { status: str, telegram_bot_enabled: bool }` — проверка доступности backend для фронтенда.
- `POST /api/chat -> { reply: str }` — простой request/response контракт для MVP чата.
- `App` — держит `messages`, `isLoading`, `backendStatus` и вызывает health/chat API.
- `MessageInput` — контролируемый input с блокировкой во время отправки.

### Test Strategy

- Backend: regression checks для `/api/health` и `/api/chat`.
- Frontend: сборка React-приложения через `npm run build`.
- Docker/VPS: сборка docker image и smoke-проверка корневого frontend маршрута после деплоя.
- Smoke: проверка, что frontend показывает доступность backend и может отрисовать ответ после отправки сообщения.

### Phases

1. **Phase 1**: Подготовить задачу, API-совместимость и конфигурацию под web-flow.
2. **Phase 2**: Реализовать React MVP question-answer frontend на основе структуры feature-ветки.
3. **Phase 3**: Обновить документацию, прогнать backend/frontend проверки и зафиксировать результаты.

### Dependencies

- Phase 2 depends on Phase 1.
- Phase 3 depends on Phase 2.

---

## Execution

### Completed

- [ ] Phase 1: Подготовить задачу, API-совместимость и конфигурацию под web-flow.
- [ ] Phase 2: Реализовать React MVP question-answer frontend на основе структуры feature-ветки.
- [ ] Phase 3: Обновить документацию, прогнать backend/frontend проверки и зафиксировать результаты.

---

## Verification

### Positive
- [ ]

### Negative
- [ ]

### Invariants
- [ ]

### Summary

---

## Review

### Invariant Checks

-

### Bug Findings

| # | Description | Severity | Confidence |
|---|-------------|----------|-------------|

### Recommendations

-

---

## Conclusion

### What was done

-

### Assumptions verified

- AS-1:

### Lessons learned

-

### Next steps

-
