# Балтийский Берег Support Bot

Команда: `Код, кофе и трансформеры`

RAG-ассистент для сервис-деска Балтийского Берега. Сервис ищет похожие тикеты и статьи в базе, строит ответ только на основе найденного контекста и возвращает citations.

## Что это такое

Внутри сервиса есть:

- `MSSQL` с backup `cleaned.bak`;
- `Qdrant` для векторного поиска;
- `FastAPI` backend;
- web-интерфейс на `React`, который открывается на `/`;
- интеграция с `Yandex AI Studio` для embeddings и ответа.

## Что нужно для запуска

Подготовьте:

- `Docker` и `docker compose`;
- `curl`;
- `Python 3` на хосте для helper-скриптов;
- доступ к `Yandex AI Studio`;
- backup `cleaned.bak`.

## Быстрый старт за 3 шага

### 1. Создайте `.env`

```bash
cp .env.example .env
```

Заполните в `.env` минимум эти значения:

```env
MSSQL_SA_PASSWORD=...
YANDEX_GPT_API_KEY=...
YANDEX_GPT_FOLDER_ID=...
```

### 2. Положите backup в `data/cleaned.bak`

```bash
mkdir -p data
curl -H "X-API-Key: YOUR_API_KEY" \
  "https://data.ai-business-spb.ru/data/baltiyskiy-bereg/cleaned.bak" \
  -o data/cleaned.bak
```

### 3. Запустите сервис одной командой

```bash
./start.sh
```

После запуска откройте:

```text
http://127.0.0.1:8000/
```

## Что делает `./start.sh`

Скрипт автоматически:

- проверяет наличие `.env`;
- проверяет наличие `data/cleaned.bak`;
- запускает `MSSQL`, `Qdrant` и `API`;
- ждёт ответа от `GET /health`;
- печатает, что делать дальше.

## Как понять, что всё работает

Проверьте статус:

```bash
./status.sh
```

Он показывает:

- состояние контейнеров;
- результат `GET /health`;
- идёт ли индексация;
- сколько документов уже проиндексировано;
- есть ли ошибка в фоне.

Пример ручной проверки:

```bash
curl http://127.0.0.1:8000/health
```

## Как пользоваться

### Вариант 1. Через браузер

Откройте:

```text
http://127.0.0.1:8000/
```

Введите вопрос сотрудника и отправьте его через форму.

### Вариант 2. Через терминал

```bash
./ask.sh "Не подключается удаленка"
```

Скрипт отправляет запрос в `POST /api/chat` и красиво печатает JSON-ответ.

Ручной вариант через `curl`:

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Не подключается удаленка"}'
```

## Как работать с сервисом каждый день

Запуск:

```bash
./start.sh
```

Проверка состояния:

```bash
./status.sh
```

Задать вопрос из терминала:

```bash
./ask.sh "Как настроить удаленку?"
```

Остановка:

```bash
./stop.sh
```

## Что означают поля в `/health`

- `status` — API отвечает;
- `rag_sync_running` — сейчас идёт индексация;
- `rag_indexed_documents` — сколько документов уже попало в `Qdrant`;
- `rag_last_error` — последняя ошибка синхронизации, если была;
- `rag_ready=true` — основной индекс уже собран и сервис готов лучше отвечать.

## Важно про первую индексацию

Первая индексация может идти долго, потому что сервис загружает и индексирует большой объём тикетов и KB.

Пока индексация не завершилась:

- ответов с `needs_human=true` может быть больше;
- safe fallback — это нормально;
- сервис специально настроен не выдумывать факты.

## Полезные команды

```bash
./start.sh
./status.sh
./ask.sh "Не подключается удаленка"
./stop.sh
docker compose logs api --tail=100
docker compose logs mssql --tail=100
docker compose logs qdrant --tail=100
uv run pytest
```

## Локальная разработка без Docker для API

Если хотите запускать только инфраструктуру в Docker, а API локально:

```bash
docker compose up -d mssql qdrant
uv sync
uv run python -m src.main
```

## Тесты

```bash
uv run pytest
```

## Структура проекта

```text
.
├─ src/
│  ├─ api.py
│  ├─ config.py
│  └─ services/
├─ frontend/react-app/
├─ tests/
├─ data/
├─ docker-compose.yml
├─ Dockerfile
├─ start.sh
├─ status.sh
├─ ask.sh
└─ stop.sh
```

## Ограничения

- качество ответов зависит от того, сколько данных уже проиндексировано;
- при rate limit со стороны Yandex индексация может идти медленнее;
- сервис консервативный: лучше отказаться от ответа, чем соврать.
