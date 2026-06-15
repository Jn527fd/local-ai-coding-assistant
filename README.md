# Local AI Coding Assistant

A self-hosted full-stack coding assistant that chats with a local Ollama
model, indexes source repositories, and answers grounded questions about an
indexed codebase. Source code and prompts stay on the machine running the app;
no cloud LLM API is required.

## Project Status

All ten planned phases are complete. The project includes the FastAPI API,
React/Vite interface, local user login, persistent Bearer API settings,
allowlisted Ollama model switching, local repository indexing, keyword-based
RAG, Docker Compose deployment, automated tests, and setup scripts.

## Features

- FastAPI backend with environment-based configuration and OpenAPI docs
- Login page backed by a local PBKDF2-hashed credentials file
- HttpOnly local browser sessions for account and model controls
- Public health endpoint and protected AI/repository endpoints
- Constant-time Bearer API-key validation
- Persistent local API-key settings and connection checks
- Model switching restricted to approved models with 7B parameters or fewer
- Streamed Ollama download progress and safe previous-model cleanup
- Up to five browser-local chats with isolated context and deletion
- Local generation through Ollama's `/api/generate` endpoint
- Recursive local repository indexing into readable JSON
- Line-aware chunks with file paths and source line ranges
- Transparent keyword-overlap retrieval for repository questions
- RAG answers that include retrieved source file paths
- React/Vite UI for health, chat, indexing, and repository questions
- Docker Compose deployment that connects to Ollama on the Linux host
- Isolated pytest coverage for health, authentication, and mocked chat
- Linux setup and local start scripts

GitHub cloning is not implemented yet. A GitHub repository can still be used
by cloning it locally and indexing its local directory.

## Architecture

```text
Browser
  |
  | HttpOnly login cookie + Authorization: Bearer <API_KEY>
  v
React/Vite frontend
  |
  v
FastAPI backend
  |-- /health --------------------------> process health
  |-- /chat ----------------------------> Ollama /api/generate
  `-- /repos
       |-- /index-local -> chunker -----> data/indexes/<repo>.json
       `-- /ask -> keyword retriever ---> grounded prompt -> Ollama
```

The frontend never sends source code to a cloud service. Ollama runs directly
on the Linux host, while the backend stores generated indexes under `data/`.
See [docs/architecture.md](docs/architecture.md) for the module-level design.

## Hardware Target

The primary target is a Linux Mint laptop with:

- An NVIDIA GPU and working Linux driver (`nvidia-smi` should succeed)
- Enough RAM, VRAM, and disk space for the selected Ollama model
- Ollama with `qwen3:4b` pulled locally
- Python 3.10 or newer
- Node.js `20.19+` or `22.12+`
- Docker Engine with the Docker Compose plugin

Ollama can fall back to CPU execution, but responses will generally be slower.
The backend and frontend themselves do not require GPU access.

## Repository Layout

```text
local-ai-coding-assistant/
|-- backend/
|   |-- app/
|   |   |-- auth/
|   |   |-- rag/
|   |   |-- routers/
|   |   |-- schemas/
|   |   |-- services/
|   |   `-- utils/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- requirements-dev.txt
|-- frontend/
|   |-- src/components/
|   |-- Dockerfile
|   `-- nginx.conf
|-- tests/
|-- scripts/
|   |-- setup.sh
|   |-- manage_credentials.py
|   `-- start.sh
|-- docs/
|-- data/
|   |-- config/
|   |-- indexes/
|   `-- repos/
|-- sample-code-repository/
|-- docker-compose.yml
|-- Makefile
`-- README.md
```

## Quick Start on Linux Mint

Install Ollama using its
[official Linux instructions](https://docs.ollama.com/linux), then pull the
default model:

```bash
ollama pull qwen3:4b
curl http://127.0.0.1:11434/api/tags
```

From the project root, run the setup helper:

```bash
bash scripts/setup.sh
```

Create or update a local user:

```bash
.venv/bin/python scripts/manage_credentials.py set YOUR_USERNAME
```

The command prompts for a password and stores only a salted PBKDF2 hash in the
ignored `data/config/credentials.json` file. Then start the app:

```bash
bash scripts/start.sh
```

Open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Interactive API docs: `http://localhost:8000/docs`

Sign in, select the circular account button, and save a private API key of at
least 16 characters. The key is persisted in browser local storage and the
ignored `data/config/app-settings.json` file.

Press `Ctrl+C` in the start-script terminal to stop both development servers.

## Run Locally Manually

Create one virtual environment at the project root:

```bash
cd ~/local-ai-coding-assistant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
mkdir -p data/config
cp credentials.example.json data/config/credentials.json
cp app-settings.example.json data/config/app-settings.json
.venv/bin/python scripts/manage_credentials.py set YOUR_USERNAME
```

Start FastAPI in terminal 1:

```bash
cd ~/local-ai-coding-assistant
source .venv/bin/activate
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start Vite in terminal 2:

```bash
cd ~/local-ai-coding-assistant/frontend
npm install
npm run dev -- --host 0.0.0.0
```

Ollama must also be running, normally as a system service:

```bash
systemctl status ollama
```

## Run with Docker Compose

Compose runs the frontend and backend. Ollama remains installed on the Linux
host and is not duplicated inside Docker.

```bash
cd ~/local-ai-coding-assistant
cp .env.example .env
test -f backend/.env || cp backend/.env.example backend/.env
mkdir -p data/config
test -f data/config/credentials.json || \
  cp credentials.example.json data/config/credentials.json
test -f data/config/app-settings.json || \
  cp app-settings.example.json data/config/app-settings.json
python3 scripts/manage_credentials.py set YOUR_USERNAME
sed -i "s/^APP_UID=.*/APP_UID=$(id -u)/" .env
docker compose up --build --detach
docker compose ps
```

Both containers should eventually report `healthy`. Sign in and configure the
Bearer key from the Account drawer.

The backend uses Linux host networking, so
`OLLAMA_BASE_URL=http://127.0.0.1:11434` reaches the host Ollama service. The
frontend is published on port `5173`, and FastAPI listens on port `8000`.

Useful lifecycle commands:

```bash
docker compose logs --follow
docker compose restart
docker compose down
```

Detached containers continue running after the terminal or SSH session closes.
The `restart: unless-stopped` policy also restarts them after a reboot once
Docker starts.

## Access from Another Computer

Find the Linux Mint machine's LAN address:

```bash
hostname -I
```

For an address such as `192.168.1.50`, set these values in the root `.env`
before building:

```dotenv
FRONTEND_API_BASE_URL=http://192.168.1.50:8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.50:5173
```

Rebuild because the frontend API URL is compiled into the Vite bundle:

```bash
docker compose up --build --detach
```

Other devices on the same trusted network can then open
`http://192.168.1.50:5173`. Do not expose ports `5173`, `8000`, or `11434`
directly to the public internet.

## API Examples

Export the same key saved in the Account drawer (or configured as the
`API_KEY` fallback):

```bash
export API_KEY="your-generated-api-key"
```

Check public endpoints:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

Chat with Ollama:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message":"Explain FastAPI dependencies briefly."}'
```

Index the included sample repository:

```bash
SAMPLE_REPO_PATH="$(realpath sample-code-repository)"

curl -X POST http://localhost:8000/repos/index-local \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"$SAMPLE_REPO_PATH\"}"
```

When using Docker, use the container-visible path instead:

```text
/repositories/sample-code-repository
```

Ask a grounded question:

```bash
curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "sample-code-repository",
    "question": "Where are the add and multiply functions implemented?"
  }'
```

Full request and error documentation is in [docs/api.md](docs/api.md).

## Repository Indexing

Supported extensions:

```text
.py .js .jsx .ts .tsx .md .json .yaml .yml .html .css
```

Ignored directories:

```text
.git node_modules .venv __pycache__ dist build
```

Indexes are readable JSON files under `data/indexes/`. Re-indexing a directory
with the same final directory name replaces its previous index.

## Tests

The tests do not require a running backend, frontend, Docker, or Ollama:

```bash
cd ~/local-ai-coding-assistant
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
python -m pytest
```

The suite verifies login, invalid credentials, persistent API settings, the
7B model policy, public health, Bearer failures, and mocked chat.

## Account and Model Settings

After login, use the circular avatar in the top-right corner.

- **API access:** Enter a key with at least 16 characters, save it, then use
  **Check connection**. The status turns connected only when the browser key
  matches the active backend key.
- **Model catalog:** Choose an approved model and select
  **Install and activate**. The UI shows unload, download, activation, cleanup,
  completion, and error states.
- **Cleanup policy:** The old model is unloaded before the download. It is
  deleted through Ollama only after the replacement downloads and becomes
  active, so a failed pull does not remove the last usable installation.

Approved models:

```text
qwen3:4b
qwen2.5-coder:3b
qwen2.5-coder:7b
llama3.2:1b
llama3.2:3b
```

The backend rejects any unlisted model, including models above 7B, even if a
request bypasses the frontend.

## Chat Storage and Deletion

Each logged-in username can keep at most five chats in that browser. Chats are
stored under a username-specific browser local-storage key; FastAPI does not
store conversation records.

Only the selected chat's latest 30 messages are sent as context with a new
request. Selecting **Delete** removes that chat and all its messages from the
application's local storage, so deleted content is not included in future
model prompts. Create-space validation prevents a sixth chat until an existing
chat is deleted.

## Configuration

Important backend variables are documented in `backend/.env.example`:

| Variable | Purpose |
| --- | --- |
| `API_KEY` | Bearer secret required by protected endpoints |
| `CREDENTIALS_FILE` | Ignored JSON file containing local user password hashes |
| `LOCAL_SETTINGS_FILE` | Ignored JSON file containing API key and active model |
| `SESSION_TTL_HOURS` | Lifetime of an in-memory login session |
| `CORS_ORIGINS` | Comma-separated frontend origins allowed by FastAPI |
| `OLLAMA_BASE_URL` | Ollama API root |
| `OLLAMA_TIMEOUT_SECONDS` | Generation request timeout |
| `MODEL_PULL_TIMEOUT_SECONDS` | Maximum model download duration |
| `DELETE_PREVIOUS_MODEL` | Delete the old active model after a successful switch |
| `DEFAULT_MODEL` | Initial active model when no local value is saved |
| `DATA_DIRECTORY` | Parent directory for generated indexes |
| `REPO_CHUNK_SIZE` | Approximate maximum characters per chunk |
| `RAG_TOP_K` | Maximum retrieved chunks supplied to the model |

Never commit real `.env` files or API keys.

Intentionally ignored local files include:

```text
.env
backend/.env
frontend/.env
data/config/credentials.json
data/config/app-settings.json
```

Safe committed templates are `credentials.example.json`,
`app-settings.example.json`, and each `.env.example`.

## Screenshots

Screenshot placeholders for the final portfolio presentation:

1. Main dashboard with backend status and successful local chat
2. Repository indexing result with file/chunk counts
3. Repository answer showing retrieved source paths

## Security and Current Limits

- This is a trusted-network, single-user project, not an internet-facing
  multi-tenant service.
- Local login sessions are held in backend memory and end after a restart.
- The Bearer key is stored in browser local storage for persistence; use the
  app only on trusted devices and protect it from untrusted scripts.
- Chat deletion removes the application's local-storage record and server
  context, but cannot promise forensic erasure from browser/device storage.
- An authenticated caller can index any path readable by the backend process.
- Retrieval uses keyword overlap, not semantic embeddings.
- Indexes are JSON files and are not designed for very large monorepositories.
- Chat responses are non-streaming.
- GitHub repositories must currently be cloned locally before indexing.

## Resume Bullet Examples

- Built a self-hosted React and FastAPI coding assistant that integrates with
  Ollama for private local LLM inference without cloud API dependencies.
- Implemented authenticated repository indexing and retrieval-augmented
  generation over source files using line-aware chunking and ranked keyword
  retrieval with source attribution.
- Containerized the frontend and backend with multi-stage Docker builds,
  health checks, persistent indexes, non-root execution, and Linux host Ollama
  connectivity.
- Added dependency-injected pytest coverage for health, authentication, and
  mocked LLM behavior, plus reproducible Linux setup documentation.

## Next Improvements

- Add embeddings and a local vector database such as Qdrant or Chroma
- Stream Ollama responses to the browser
- Add GitHub clone/update support with safe credential handling
- Add language-aware parsing with Tree-sitter
- Add repository management, index deletion, and index freshness metadata
- Add rate limiting, per-user authentication, and an HTTPS reverse proxy
- Expand tests for repository indexing, RAG ranking, and frontend behavior
- Add CI for linting, tests, and Docker image builds

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Linux Mint setup](docs/setup.md)

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
