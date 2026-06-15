#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ ! -x .venv/bin/python ]]; then
    echo "Missing .venv. Run: bash scripts/setup.sh" >&2
    exit 1
fi

if [[ ! -f backend/.env || ! -f data/config/credentials.json ]]; then
    echo "Missing local configuration. Run: bash scripts/setup.sh" >&2
    exit 1
fi

if ! grep -q '"username"' data/config/credentials.json; then
    echo "No local login exists. Run:" >&2
    echo "  .venv/bin/python scripts/manage_credentials.py set YOUR_USERNAME" >&2
    exit 1
fi

if [[ ! -d frontend/node_modules ]]; then
    echo "Missing frontend dependencies. Run: bash scripts/setup.sh" >&2
    exit 1
fi

backend_pid=""
frontend_pid=""

cleanup() {
    trap - EXIT INT TERM
    [[ -n "$backend_pid" ]] && kill "$backend_pid" 2>/dev/null || true
    [[ -n "$frontend_pid" ]] && kill "$frontend_pid" 2>/dev/null || true
    wait "$backend_pid" "$frontend_pid" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

echo "Starting FastAPI at http://localhost:8000..."
(
    cd backend
    ../.venv/bin/python -m uvicorn app.main:app \
        --reload \
        --host 0.0.0.0 \
        --port 8000
) &
backend_pid=$!

echo "Starting Vite at http://localhost:5173..."
npm --prefix frontend run dev -- --host 0.0.0.0 --strictPort &
frontend_pid=$!

echo "Press Ctrl+C to stop both services."
wait -n "$backend_pid" "$frontend_pid"
