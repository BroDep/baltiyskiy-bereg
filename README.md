# Baltiyskiy Bereg — Service Desk AI Assistant

![Hackathon](https://img.shields.io/badge/Hackathon-AI%20Business%20SPB%202026-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![MSSQL](https://img.shields.io/badge/MSSQL-2019-red)
![YandexGPT](https://img.shields.io/badge/YandexGPT-LLM-orange)

LLM-чатбот для сервис-деска «Балтийский Берег». Помогает сотрудникам находить решения в истории тикетов и базе знаний.

## 🎯 О проекте

**ООО «ТД «Балтийский Берег»** — один из крупнейших производителей рыбной продукции в России. Более 350 наименований, ~1000 сотрудников.

**Проблема:** Отсутствует структурированная база знаний. Вся экспертиза — в исторических тикетах (~104 000) и статьях (~1 060).

**Решение:** LLM-бот, который ищет релевантные решения и отвечает на вопросы сотрудников.

## 🚀 Быстрый старт

### 1. Клонирование и настройка

```bash
git clone https://github.com/BroDep/baltiyskiy-bereg.git
cd baltiyskiy-bereg

cp .env.example .env
# Заполните .env (см. секцию Configuration)
```

### 2. Запуск

```bash
# Запуск всех сервисов
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f api
```

### 3. Проверка

```bash
# Health check
curl http://localhost:8000/health

# Тестовый запрос к API
curl http://localhost:8000/
```

## 📁 Структура проекта

```
baltiyskiy-bereg/
├── src/                    # Исходный код приложения
│   └── main.py             # FastAPI entry point
├── data/                   # Дампы БД (не в гите)
├── docker-compose.yml      # Docker services
├── Dockerfile              # App container
├── pyproject.toml          # Python dependencies
├── restore-db.sh           # Скрипт восстановления БД
└── .agents/                # Документация для AI-агентов
    ├── AGENTS.md           # Гайдлайны для агентов
    ├── index.md            # Обзор проекта
    └── skills/             # Reusable skills
```

## ⚙️ Configuration

Скопируйте `.env.example` в `.env` и заполните:

```bash
# API-ключ хакатона (platform.ai-business-spb.ru)
API_KEY=your-team-api-key

# MSSQL Database
MSSQL_SA_PASSWORD=YourStrong!Pass123
MSSQL_HOST=localhost
MSSQL_PORT=1433
MSSQL_DATABASE=service_desk_tdbb
MSSQL_USER=SA

# YandexGPT
YANDEX_GPT_API_KEY=your-api-key
YANDEX_GPT_FOLDER_ID=your-folder-id
YANDEX_GPT_MODEL=yandexgpt/latest
```

### Получение API-ключа YandexGPT

1. [Yandex Cloud Console](https://console.yandex.cloud/)
2. Создайте сервисный аккаунт с ролью `ai.languageModels.user`
3. Создайте API-ключ
4. Скопируйте `folder_id` и ключ в `.env`

## 🗄️ База данных

### Схема

| Таблица | Строк | Описание |
|---------|-------|---------|
| `Task` | 104 395 | Тикеты (Name, Description, Comment HTML) |
| `KBDocument` | 1 060 | Статьи базы знаний |
| `TaskFieldValues` | — | Custom-поля |
| `TaskExpenses` | — | Трудозатраты |
| `Service`, `TaskType`, `Status`, `Priority` | — | Lookup-таблицы |

### Ключевые поля Task

- `Name` — краткое название
- `Description` — описание
- `Comment` — **HTML Q&A переписка** (главный источник для RAG)
- `StatusId`, `ServiceId`, `TypeId` — категоризация

### Загрузка данных

```bash
# Через curl
curl -H "X-API-Key: YOUR_API_KEY" \
     https://data.ai-business-spb.ru/data/baltiyskiy-bereg/cleaned.bak \
     -o data/cleaned.bak
```

## 🔧 API Endpoints

| Endpoint | Method | Описание |
|----------|--------|----------|
| `/` | GET | Информация о сервисе |
| `/health` | GET | Health check |
| `/api/search` | POST | Поиск по тикетам и KB |
| `/api/chat` | POST | Chat с ботом |
| `/api/classify` | POST | Классификация заявки |

## 📊 Требования

### Performance

| Метрика | Значение |
|---------|---------|
| Время ответа | ≤ 30 сек |
| Нагрузка | 30–50 запросов/сутки |
| Автоматизация | ≥ 50% запросов |

### Deployment

- **Пилот:** SaaS
- **Продуктив:** On-premise (Docker)

### Интеграции (вне MVP)

- Telegram Bot
- Max (ICQ)
- Битрикс24

## 🧪 Тестирование

```bash
# Установка зависимостей
uv sync

# Линтинг
uv run ruff check .

# Тесты (когда будут)
uv run pytest

# Полная проверка
uv run ruff check . && uv run pytest
```

## 📈 Roadmap

- [x] Starter project setup
- [x] CI/CD pipeline
- [ ] YandexGPT integration
- [ ] RAG search по тикетам
- [ ] Telegram bot
- [ ] Классификация заявок
- [ ] Admin panel
- [ ] Dashboard

## 👥 Команда

**Контакты:** www.sooskolkos@gmail.com

**GitHub:** https://github.com/BroDep/baltiyskiy-bereg

**Платформа:** https://app.ai-business-spb.ru

## 📄 License

MIT

## 🏆 Критерии оценки (хакатон)

| Критерий | Описание |
|----------|---------|
| Техническая реализация | Бот работает, ≤30 сек, корректный ввод |
| Бизнес-ценность | ≤50% эскалаций |
| Готовность | README, инструкция запуска |
| Инновационность | Подход к извлечению знаний из 104K тикетов |
