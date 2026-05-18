#!/usr/bin/env bash

set -euo pipefail

BASE_PYTHON="${BASE_PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

if ! command -v "$BASE_PYTHON" >/dev/null 2>&1; then
  echo "Python executable not found: $BASE_PYTHON" >&2
  exit 1
fi

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$BASE_PYTHON" -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
  if ! "$VENV_DIR/bin/python" -m ensurepip --upgrade >/dev/null 2>&1; then
    echo "pip is missing inside $VENV_DIR and could not be bootstrapped automatically." >&2
    echo "Install full Python support first, then retry: sudo apt install python3-full" >&2
    exit 1
  fi
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r backend/requirements.txt
