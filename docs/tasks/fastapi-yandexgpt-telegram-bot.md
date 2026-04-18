# Task: FastAPI YandexGPT Telegram Bot

**Created:** 2026-04-18
**Status:** design

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

- AS-1: Для YandexGPT можно использовать OpenAI-совместимый chat/completions интерфейс с API-ключом и folder ID.
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
| | | |

### Interfaces

-

### Test Strategy

-

### Phases

1. **Phase 1**: Уточнить структуру файлов и зависимости.

### Dependencies

-

---

## Execution

### Completed

- [ ]

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
