#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

docker compose ps

echo
echo "Health:"
if curl -fsS http://127.0.0.1:8000/health >/tmp/baltiyskiy-bereg-health-status.json 2>/dev/null; then
    python3 -m json.tool /tmp/baltiyskiy-bereg-health-status.json
else
    echo "API пока не отвечает"
fi
