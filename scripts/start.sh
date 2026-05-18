#!/usr/bin/env bash

set -euo pipefail

if [[ -x ".venv/bin/python" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable not found: $PYTHON_BIN" >&2
  echo "Set PYTHON_BIN to an installed interpreter, for example: PYTHON_BIN=python3 npm run start" >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c "import uvicorn" >/dev/null 2>&1; then
  echo "Backend dependencies are missing for $PYTHON_BIN." >&2
  echo "Install them first with: npm run setup:backend" >&2
  exit 1
fi

cleanup() {
  trap - SIGINT SIGTERM EXIT
  [[ -n "${FRONTEND_PID:-}" ]] && kill "$FRONTEND_PID" 2>/dev/null || true
  [[ -n "${BACKEND_PID:-}" ]] && kill "$BACKEND_PID" 2>/dev/null || true
}

trap cleanup SIGINT SIGTERM EXIT

npm run dev &
FRONTEND_PID=$!

"$PYTHON_BIN" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8483 --reload &
BACKEND_PID=$!

wait -n "$FRONTEND_PID" "$BACKEND_PID"
