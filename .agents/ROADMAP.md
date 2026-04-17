# Roadmap — Baltiyskiy Bereg

## Phase 1: Foundation (MVP)

| ID | Фича | Описание | Приоритет | Контракт |
|----|------|---------|-----------|----------|
| **F-001** | Исправить Dockerfile | Multi-stage build, uv sync, минимум образ | P0 | [#11](https://github.com/BroDep/baltiyskiy-bereg/issues/11) |
| **F-002** | Структура модулей | src/{database,services,models,api} | P0 | [#12](https://github.com/BroDep/baltiyskiy-bereg/issues/12) |
| **F-003** | YandexGPT integration | Подключение к API, базовые запросы | P0 | [#13](https://github.com/BroDep/baltiyskiy-bereg/issues/13) |
| **F-004** | Database client | Подключение к MSSQL, parameterized queries | P0 | [#14](https://github.com/BroDep/baltiyskiy-bereg/issues/14) |
| **F-005** | RAG Search | Поиск по тикетам и KB-статьям | P0 | [#15](https://github.com/BroDep/baltiyskiy-bereg/issues/15) |
| **F-006** | Chat API | POST /api/chat с контекстом из RAG | P0 | [#16](https://github.com/BroDep/baltiyskiy-bereg/issues/16) |

---

## Phase 2: Core Features

| ID | Фича | Описание | Приоритет | Контракт |
|----|------|---------|-----------|----------|
| **F-010** | Ticket Classification | Предсказание Service/Type/Priority | P1 | [#17](https://github.com/BroDep/baltiyskiy-bereg/issues/17) |
| **F-011** | Telegram Bot | Интеграция с Telegram Bot API | P1 | [#18](https://github.com/BroDep/baltiyskiy-bereg/issues/18) |
| **F-012** | Response Caching | Кеширование ответов для скорости | P1 | [#19](https://github.com/BroDep/baltiyskiy-bereg/issues/19) |
| **F-013** | Web UI | Swagger/OpenAPI + простой frontend | P2 | [#20](https://github.com/BroDep/baltiyskiy-bereg/issues/20) |

---

## Phase 3: Enhancement

| ID | Фича | Описание | Приоритет | Контракт |
|----|------|---------|-----------|----------|
| **F-020** | Admin Panel | Управление настройками | P2 | #issue |
| **F-021** | Dashboard | Статистика запросов, качество ответов | P2 | #issue |
| **F-022** | Max Integration | Бот для Max (ICQ) | P3 | #issue |
| **F-023** | Bitrix24 Integration | Интеграция с Битрикс24 | P3 | #issue |

---

## Phase 4: Production

| ID | Фича | Описание | Приоритет | Контракт |
|----|------|---------|-----------|----------|
| **F-030** | Authentication | OAuth/JWT для API | P2 | #issue |
| **F-031** | Rate Limiting | Защита от спама | P2 | #issue |
| **F-032** | Monitoring | Логи, метрики, алерты | P2 | #issue |
| **F-033** | On-premise Deploy | Ansible/Helm для prod | P2 | #issue |

---

## Future Ideas

- [ ] Голосовой ввод (speech-to-text)
- [ ] Многоязычность (английский для экспорта)
- [ ] ML fine-tuning на исторических тикетах
- [ ] Интеграция с IntraService API
- [ ] A/B тестирование ответов

---

## Milestones

| Milestone | Дата | Фичи |
|-----------|------|------|
| **v0.1.0** | Sprint 1 | F-001 → F-004 (Infrastructure) |
| **v0.2.0** | Sprint 2 | F-005 → F-006 (Core Chat) |
| **v0.3.0** | Sprint 3 | F-010 → F-012 (Telegram + Classification) |
| **v1.0.0** | Хакатон | MVP готов к демо |

---

## Tech Debt

- [ ] Добавить pytest тесты
- [ ] Добавить mypy type checking
- [ ] Настроить pre-commit hooks
- [ ] Добавить CI/CD healthchecks для API
