# Балтийский Берег Support Bot

Команда: `Код, кофе и трансформеры`

RAG-ассистент для сервис-деска Балтийского Берега. Сервис отвечает на вопросы сотрудников только на основе MSSQL-базы сервис-деска и базы знаний, использует `Qdrant` для поиска, модели `Yandex AI Studio` для embeddings и генерации, делает rerank, citations и safe fallback, если уверенности недостаточно.

## Что умеет сервис

- читать тикеты и KB из MSSQL в read-only режиме;
- индексировать данные в `Qdrant`;
- искать похожие кейсы по embeddings;
- rerank'ить найденные документы;
- генерировать grounded-ответы с citations;
- отказывать в ответе, если данных недостаточно или есть риск галлюцинации;
- отдавать ответы через `FastAPI` и Telegram-бота.

## Стек и зависимости

- `Python 3.11+`
- `FastAPI`
- `aiogram`
- `httpx`
- `pymssql`
- `qdrant-client`
- `pydantic-settings`
- `uvicorn`
- `pytest`, `pytest-asyncio`
- `Docker` и `docker compose`
- `MSSQL Server 2019`
- `Qdrant`
- `YandexGPT` и embeddings `text-search-doc/latest`, `text-search-query/latest`

## Требования для запуска

Нужно подготовить:

- `Docker` и `docker compose`
- `uv`
- доступ к `Yandex AI Studio`
- дамп базы `cleaned.bak`
- файл `.env` на основе `.env.example`

Минимально обязательные переменные окружения:

```env
MSSQL_SA_PASSWORD=...
YANDEX_GPT_API_KEY=...
YANDEX_GPT_FOLDER_ID=...
```

Остальные переменные уже есть в `.env.example`.

## Структура проекта

```text
.
├─ src/
│  ├─ api.py
│  ├─ config.py
│  └─ services/
│     ├─ mssql_knowledge_base.py
│     ├─ qdrant_store.py
│     ├─ rag_models.py
│     ├─ rag_pipeline.py
│     ├─ rag_sync.py
│     ├─ telegram_bot.py
│     ├─ text_normalization.py
│     └─ yandex_gpt.py
├─ tests/
├─ docs/
├─ data/
├─ docker-compose.yml
├─ Dockerfile
├─ pyproject.toml
└─ .env.example
```

Ключевые файлы:

- `src/api.py` - FastAPI-приложение и endpoints
- `src/services/rag_pipeline.py` - retrieval, rerank, answer, verify
- `src/services/rag_sync.py` - фоновая синхронизация MSSQL -> Qdrant
- `src/services/mssql_knowledge_base.py` - извлечение тикетов и KB из MSSQL
- `src/services/qdrant_store.py` - работа с коллекцией Qdrant
- `src/services/yandex_gpt.py` - completion и embeddings через Yandex AI Studio
- `docker-compose.yml` - локальный деплой MSSQL, Qdrant и API

## Подготовка данных

Скачайте `cleaned.bak` и положите его в `data/cleaned.bak`.

Пример:

```bash
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://data.ai-business-spb.ru/data/baltiyskiy-bereg/cleaned.bak" \
  -o data/cleaned.bak
```

## Быстрый локальный запуск через Docker

1. Подготовьте `.env`:

```bash
cp .env.example .env
```

2. Заполните секреты в `.env`.

3. Поднимите все сервисы:

```bash
docker compose up -d --build
```

4. Проверьте здоровье API:

```bash
curl http://127.0.0.1:8000/health
```

5. Дождитесь первичной индексации.

Важно:

- первый `full sync` может идти долго, потому что индексируются десятки тысяч тикетов;
- пока индексация не завершена, сервис может чаще отдавать safe fallback;
- это нормальное поведение: бот лучше откажется, чем соврёт.

## Локальная разработка без запуска API в Docker

Если хотите запускать `api` локально, а `MSSQL` и `Qdrant` оставить в Docker:

1. Поднимите инфраструктуру:

```bash
docker compose up -d mssql qdrant
```

2. Установите зависимости:

```bash
uv sync
```

3. Запустите API:

```bash
uv run python -m src.main
```

## Проверка работы

Healthcheck:

```bash
curl http://127.0.0.1:8000/health
```

Тестовый запрос:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Не подключается удаленка"}'
```

Пример ответа:

```json
{
  "reply": "Не могу уверенно ответить только по данным из базы. Лучше передать вопрос специалисту.",
  "citations": [],
  "confidence": 0.64,
  "grounded": false,
  "needs_human": true,
  "reason": "low_confidence"
}
```

Или, если данных уже достаточно:

```json
{
  "reply": "Проверьте UniVPN и 2MFA Контур.Коннект. [KB#101]",
  "citations": [
    {
      "label": "KB#101",
      "source_type": "kb",
      "source_id": 101,
      "title": "UniVPN и 2MFA",
      "excerpt": "Проверьте UniVPN и 2MFA Контур.Коннект."
    }
  ],
  "confidence": 0.82,
  "grounded": true,
  "needs_human": false,
  "reason": "verified"
}
```

## Тесты

Запуск тестов:

```bash
uv run pytest
```

Проверка импорта и синтаксиса:

```bash
uv run python -m compileall src tests
```

## Деплой

Самый простой вариант деплоя - через `docker compose`.

Шаги:

1. Клонировать репозиторий.
2. Положить `cleaned.bak` в `data/`.
3. Создать `.env` из `.env.example`.
4. Заполнить секреты.
5. Выполнить:

```bash
docker compose up -d --build
```

Проверка после деплоя:

```bash
docker compose ps
docker compose logs api --tail=100
curl http://127.0.0.1:8000/health
```

## Поведение RAG

- тикет индексируется как один chunk;
- KB режется на chunks после очистки HTML;
- ответ строится только по найденным документам;
- citations обязательны;
- после генерации ответ проходит дополнительную проверку;
- если уверенность недостаточна, сервис возвращает отказ.

## Ограничения

- качество ответов зависит от полноты первичного бэкфилла;
- пока `Qdrant` не проиндексировал значимую часть базы, fallback'ов будет больше;
- при rate limit'ах Yandex embeddings синхронизация может идти медленнее;
- сервис специально настроен консервативно: не выдумывать ответ.

## Команды, которые пригодятся

```bash
docker compose up -d --build
docker compose ps
docker compose logs api --tail=100
docker compose logs qdrant --tail=100
uv sync
uv run pytest
uv run python -m src.main
```
