# Setup Guide

## Status

The Phase 6 FastAPI backend can authenticate requests, send chat prompts to
local Ollama models, index local repositories into JSON, and answer grounded
questions over those indexes. Frontend and Docker instructions will be added
in later phases.

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

Repository indexes are stored under `DATA_DIRECTORY/indexes`. When the backend
is launched from `backend/`, the example value `../data` points to the project
root's `data/` directory. `REPO_CHUNK_SIZE` controls the approximate maximum
characters in each line-aware chunk. `RAG_TOP_K` controls how many relevant
chunks are included in a repository prompt, and `RAG_MODEL` selects the Ollama
model used for repository answers.

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

## Index a Repository

The project includes `sample-code-repository/` as a ready-to-index fixture.
From the project root, compute its absolute path and call the endpoint:

```bash
SAMPLE_REPO_PATH="$(realpath sample-code-repository)"

curl -X POST http://localhost:8000/repos/index-local \
  -H "Authorization: Bearer your-generated-value" \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"$SAMPLE_REPO_PATH\"}"
```

Inspect the generated index:

```bash
ls -lh data/indexes
python -m json.tool data/indexes/sample-code-repository.json | less
```

Re-indexing a repository with the same directory name replaces its previous
JSON index.

## Ask About the Sample Repository

After indexing the fixture, ask a question:

```bash
curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer your-generated-value" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "sample-code-repository",
    "question": "Where are the add and multiply functions implemented?"
  }'
```

The response should contain an answer from Ollama and one or more relative
source paths, including `sample_app/calculator.py` for this question.

If the index is missing, run `/repos/index-local` first. If Ollama is
unavailable, verify it directly with:

```bash
curl http://localhost:11434/api/tags
```
