# TODO: Flask-сервер — раздаёт React-сборку и проксирует запросы к FastAPI
#
# Маршруты:
#   GET  /           → отдаёт react-app/build/index.html
#   GET  /static/..  → отдаёт статику React-сборки (JS/CSS/assets)
#   POST /api/chat   → проксирует на FastAPI POST /chat (API_BASE_URL из .env)
#   GET  /api/health → проксирует на FastAPI GET /health
#
# Запуск:
#   cd frontend && flask --app flask_app run --port 5000
#   (React-сборка должна быть в react-app/build/ — выполнить npm run build)
#
# Переменные окружения:
#   API_BASE_URL=http://localhost:8000  (адрес FastAPI)
#   FLASK_ENV=development / production
