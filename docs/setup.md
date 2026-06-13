# Setup Guide

## Status

The Phase 9 application includes the FastAPI backend, React/Vite frontend,
Docker Compose support, and isolated pytest coverage for health,
authentication, and chat behavior.

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

## Run the Frontend on Linux Mint

Use Node.js 20.19 or newer. Keep the backend running in its terminal and open
a second terminal:

```bash
cd ~/local-ai-coding-assistant/frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173` in a browser.

If the backend uses a different host or port, edit `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

In the interface:

1. Confirm the status panel reports that FastAPI is connected.
2. Paste the value from `backend/.env` into the API-key field.
3. Send a message to `qwen3:4b` in the chat panel.
4. Index the absolute path returned by
   `realpath ~/local-ai-coding-assistant/sample-code-repository`.
5. Ask where the `add` and `multiply` functions are implemented.

The API key remains in React memory for the current tab and is not persisted
to browser storage.

## Run with Docker Compose on Linux Mint

The Docker setup assumes these commands succeed:

```bash
docker --version
docker compose version
systemctl is-active ollama
```

Stop the manually started Uvicorn and Vite development servers with `Ctrl+C`
before starting Compose. Ports `8000` and `5173` must be free.

From the project root, prepare the Compose environment:

```bash
cd ~/local-ai-coding-assistant
cp .env.example .env
sed -i "s/^APP_UID=.*/APP_UID=$(id -u)/" .env
test -f backend/.env || cp backend/.env.example backend/.env
```

The root `.env` configures Docker build and mount behavior:

```dotenv
APP_UID=1000
FRONTEND_API_BASE_URL=http://localhost:8000
LOCAL_REPOS_ROOT=.
```

Use your actual user ID for `APP_UID`; the `sed` command above does this
automatically. This lets the non-root backend container write generated JSON
indexes to the host `data/` directory.

Keep the private API key in `backend/.env`:

```dotenv
API_KEY=your-generated-value
```

Build and start:

```bash
docker compose up --build --detach
docker compose ps
```

Both services should eventually report `healthy`. Open:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`
- Backend API docs: `http://localhost:8000/docs`

Follow startup and request logs:

```bash
docker compose logs --follow
```

Stop the application:

```bash
docker compose down
```

## Host Ollama Connection

The Linux Compose configuration gives the backend container host networking.
As a result, this container setting reaches Ollama running on the laptop:

```dotenv
OLLAMA_BASE_URL=http://127.0.0.1:11434
```

You do not need to run Ollama in Docker or change its default listening
address. Verify it before starting Compose:

```bash
curl http://127.0.0.1:11434/api/tags
```

If the backend container cannot reach Ollama, check:

```bash
systemctl status ollama
docker compose logs backend
```

## Repository Paths in Docker

Containers cannot use host paths such as
`/home/chuy/local-ai-coding-assistant/sample-code-repository` directly. The
Compose file mounts `LOCAL_REPOS_ROOT` at `/repositories` inside the backend.

With the default root setting:

```dotenv
LOCAL_REPOS_ROOT=.
```

use this path in the frontend indexing form:

```text
/repositories/sample-code-repository
```

To index repositories stored under `/home/chuy/projects`, change the root
`.env`:

```dotenv
LOCAL_REPOS_ROOT=/home/chuy/projects
```

Recreate the containers:

```bash
docker compose up --build --detach
```

A repository at `/home/chuy/projects/example-api` is then visible to the
backend as:

```text
/repositories/example-api
```

The repository mount is read-only. Generated indexes are written separately
to the persistent host `data/indexes/` directory.

## Run Automated Tests

From the project root, activate the repository virtual environment and install
the development requirements:

```bash
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
```

Run the complete backend suite:

```bash
python -m pytest
```

The tests use an in-memory FastAPI client, a temporary data directory, and a
mock Ollama service. The backend, frontend, and Ollama do not need to be
running.
