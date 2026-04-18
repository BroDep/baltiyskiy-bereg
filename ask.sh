#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUESTION="${*:-}"

if [ -z "$QUESTION" ]; then
    echo "Использование: ./ask.sh \"Ваш вопрос\""
    exit 1
fi

cd "$ROOT_DIR"

PAYLOAD="$(python3 - "$QUESTION" <<'PY'
import json
import sys

print(json.dumps({"message": sys.argv[1]}, ensure_ascii=False))
PY
)"

curl -fsS \
    -X POST \
    http://127.0.0.1:8000/api/chat \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD" | python3 -m json.tool
