#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

for command_name in python3 npm; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        echo "Required command not found: $command_name" >&2
        exit 1
    fi
done

if [[ ! -d .venv ]]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
fi

echo "Installing backend and test dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements-dev.txt

echo "Installing frontend dependencies..."
npm --prefix frontend install

if [[ ! -f backend/.env ]]; then
    cp backend/.env.example backend/.env
    echo "Created backend/.env from its example."
fi

if [[ ! -f frontend/.env ]]; then
    cp frontend/.env.example frontend/.env
    echo "Created frontend/.env from its example."
fi

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created root .env from its example."
fi

mkdir -p data/indexes data/repos data/config

if [[ ! -f data/config/credentials.json ]]; then
    cp credentials.example.json data/config/credentials.json
    chmod 600 data/config/credentials.json
    echo "Created data/config/credentials.json from its safe template."
fi

if [[ ! -f data/config/app-settings.json ]]; then
    cp app-settings.example.json data/config/app-settings.json
    chmod 600 data/config/app-settings.json
    echo "Created data/config/app-settings.json from its safe template."
fi

echo
echo "Setup complete."
echo "Create a local login with:"
echo "  .venv/bin/python scripts/manage_credentials.py set YOUR_USERNAME"
echo "Then ensure Ollama is running and run: bash scripts/start.sh"
