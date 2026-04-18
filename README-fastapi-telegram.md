# README — FastAPI + Telegram + YandexGPT

Этот файл содержит документацию по добавленному серверу FastAPI и Telegram-боту.

## Что делает сервис

- поднимает FastAPI API;
- запускает Telegram-бота в режиме long polling;
- принимает текстовые сообщения из Telegram;
- отправляет их в YandexGPT;
- возвращает ответ обратно в тот же чат;
- пишет логи в stdout.

## Установка

```bash
uv sync
cp .env.example .env
```

Заполните в `.env` обязательные переменные:

```env
YANDEX_GPT_API_KEY=...
YANDEX_GPT_FOLDER_ID=...
TELEGRAM_BOT_TOKEN=...
```

## Запуск

```bash
uv run python -m src.main
```

## HTTP endpoints

- `GET /` — простая проверка, что API запущено;
- `GET /health` — healthcheck приложения;
- `POST /api/chat` — прямой вызов YandexGPT без Telegram.

Пример локального запроса:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Привет!"}'
```

## Переменные окружения

### YandexGPT

```env
YANDEX_GPT_API_KEY=your-api-key
YANDEX_GPT_FOLDER_ID=your-folder-id
YANDEX_GPT_MODEL=yandexgpt/latest
YANDEX_GPT_TIMEOUT_SECONDS=30
YANDEX_GPT_TEMPERATURE=0.2
YANDEX_GPT_MAX_TOKENS=800
YANDEX_GPT_SYSTEM_PROMPT=Ты полезный IT-ассистент компании Балтийский Берег. Отвечай кратко, понятно и по делу.
```

Сервис использует endpoint:

```text
https://llm.api.cloud.yandex.net/foundationModels/v1/completion
```

Запрос формируется с `modelUri` вида `gpt://<folder_id>/<model>` и заголовком `Authorization: Api-Key <ключ>`.

### Telegram / приложение

```env
TELEGRAM_BOT_ENABLED=true
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
APP_NAME=Baltiyskiy Bereg Bot API
APP_HOST=0.0.0.0
APP_PORT=8000
APP_RELOAD=false
LOG_LEVEL=INFO
```

## Логирование

- HTTP-запросы логируются middleware в FastAPI;
- обращения к YandexGPT логируются без вывода секретов;
- ошибки Telegram/YandexGPT логируются и возвращают безопасный fallback.

## Проверки

```bash
uv run pytest
```

После запуска можно написать Telegram-боту текстовое сообщение и проверить полный поток Telegram → YandexGPT → Telegram.
