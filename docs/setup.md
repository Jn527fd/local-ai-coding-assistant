# Setup Guide

## Status

The Phase 4 FastAPI backend can authenticate requests and send chat prompts to
local Ollama models. Frontend and Docker instructions will be added in later
phases.

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
# Edit .env and replace the API_KEY placeholder before starting the server.
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

## Configure the API Key

Generate a random key:

```bash
openssl rand -hex 32
```

Set the generated value in `backend/.env`:

```dotenv
API_KEY=your-generated-value
```

Send the same value to protected endpoints:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your-generated-value" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:4b","message":"Hello"}'
```

Do not commit `backend/.env` or share its API key.

## Prepare Ollama

Check that Ollama is available:

```bash
ollama --version
```

Pull and verify the default model:

```bash
ollama pull qwen3:4b
ollama list
```

Test Ollama directly:

```bash
curl http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:4b","prompt":"Reply with hello.","stream":false}'
```

For a backend running directly on Linux Mint, keep this `.env` value:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=120
```

If Ollama is not already running as a service, start it in another terminal:

```bash
ollama serve
```

After starting the FastAPI backend, send an authenticated chat request:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer your-generated-value" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:4b","message":"Write a Python hello-world function."}'
```
