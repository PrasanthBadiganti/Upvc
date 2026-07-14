#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -x "$ROOT/backend/.venv/bin/python" ]]; then
  "$ROOT/setup-local.sh"
fi
[[ -f "$ROOT/frontend/dist/index.html" ]] || { echo "Prebuilt frontend is missing."; exit 1; }
echo "Application: http://127.0.0.1:8000"
echo "API docs:   http://127.0.0.1:8000/docs"
cd "$ROOT/backend"
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
