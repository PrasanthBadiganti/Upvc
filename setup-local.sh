#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"

echo "UPVC Pro local setup (prebuilt frontend; Node/npm not required)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || { echo "Python 3.11+ is required."; exit 1; }

if [[ ! -x .venv/bin/python ]]; then
  "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -m pip install --disable-pip-version-check --upgrade pip
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
[[ -f "$ROOT/frontend/dist/index.html" ]] || { echo "Prebuilt frontend is missing."; exit 1; }
.venv/bin/python -c "from app.main import app; print('Application import successful')"
echo "Setup completed. Run ./start-local.sh"
