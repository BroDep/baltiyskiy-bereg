# README — Frontend Web Chat

Этот файл описывает новый web channel вместо Telegram для простого сценария вопрос-ответ.

## Что входит в MVP

- React-интерфейс чата;
- проверка доступности backend через `GET /api/health`;
- отправка вопроса через `POST /api/chat`;
- отображение ответа ассистента и состояния отправки.

## Что не входит в этот шаг

- авторизация;
- история чатов;
- аналитика;
- список тикетов;
- auth/history/analytics API из более широкого frontend-контракта.

## Структура

```text
frontend/react-app/
```

## Запуск backend

```bash
uv run python -m src.main
```

Если предварительно собрать frontend через `npm run build`, backend начнет отдавать его на корневом маршруте `/`.

## Запуск frontend

```bash
cd frontend/react-app
npm install
npm start
```

По умолчанию dev server проксирует API-запросы на `http://localhost:8000`.

## Сборка frontend

```bash
cd frontend/react-app
npm install
npm run build
```

После этого можно открыть:

```text
http://localhost:8000/
```

## Docker / VPS

`Dockerfile` собирает React build в отдельном stage и копирует его в Python image. После `docker compose up -d --build api` фронтенд доступен на `/`, а API — на `/api/*`.

## API, которые использует MVP frontend

- `GET /api/health`
- `POST /api/chat`

## Переменные окружения backend

```env
TELEGRAM_BOT_ENABLED=false
FRONTEND_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```
