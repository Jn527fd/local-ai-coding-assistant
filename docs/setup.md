# Setup Guide

## Status

The Phase 2 FastAPI backend can be run locally. Frontend and Docker instructions
will be added in later phases.

## Target Environment

- Linux Mint
- NVIDIA GPU with supported drivers
- Docker and Docker Compose
- Ollama
- Python for local backend development
- Node.js and npm for local frontend development

## Planned Setup Flow

1. Install and verify the NVIDIA drivers.
2. Install Ollama and pull a small model such as `qwen3:4b`.
3. Create local environment files from the committed `.env.example` files.
4. Install backend and frontend dependencies.
5. Start the backend and frontend locally, or use Docker Compose.
6. Verify the health endpoint and Ollama connectivity.

No secrets will be committed to source control.

## Run the Backend on Linux Mint

From the repository root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` to inspect the generated OpenAPI
documentation.

## Backend Configuration

The backend reads configuration from environment variables. For local
development, copy `backend/.env.example` to `backend/.env` and edit the copied
file. The `.env` file is ignored by Git.

`CORS_ORIGINS` is a comma-separated list. Its default value allows the planned
Vite frontend at both `http://localhost:5173` and
`http://127.0.0.1:5173`.
