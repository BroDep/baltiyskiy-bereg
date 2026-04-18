#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: docker не найден. Установите Docker и Docker Compose."
    exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
    echo "ERROR: curl не найден. Установите curl и повторите запуск."
    exit 1
fi

mkdir -p data

if [ ! -f .env ]; then
    cp .env.example .env
    echo "Создан .env из .env.example. Заполните секреты и запустите ./start.sh ещё раз."
    exit 1
fi

if [ ! -f data/cleaned.bak ]; then
    echo "ERROR: не найден файл data/cleaned.bak"
    echo "Скачайте backup и положите его в data/cleaned.bak"
    exit 1
fi

chmod +x restore-db.sh

echo "Поднимаю MSSQL, Qdrant и API..."
docker compose up -d --build

echo "Жду ответа от API на /health..."
for _ in $(seq 1 90); do
    if curl -fsS http://127.0.0.1:8000/health >/tmp/baltiyskiy-bereg-health.json 2>/dev/null; then
        break
    fi
    sleep 2
done

echo
if [ -f /tmp/baltiyskiy-bereg-health.json ]; then
    echo "Сервис запущен. Текущее состояние:"
    python3 -m json.tool /tmp/baltiyskiy-bereg-health.json || true
else
    echo "API ещё не ответил. Проверьте состояние через ./status.sh"
fi

echo
echo "Открыть веб-интерфейс: http://127.0.0.1:8000/"
echo "Проверить статус:      ./status.sh"
echo "Задать вопрос:         ./ask.sh \"Не подключается удаленка\""
echo "Остановить сервис:     ./stop.sh"
