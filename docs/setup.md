# Linux Mint Setup Guide

## Prerequisites

- Linux Mint
- Python 3.10+ with `venv`
- Node.js `20.19+` or `22.12+` with npm
- Docker Engine with the Compose plugin
- Ollama
- Git and curl
- An NVIDIA GPU is useful for larger models, but CPU-only smoke testing is
  supported with tiny models

Verify:

```bash
python3 --version
node --version
npm --version
docker compose version
ollama --version
```

Optional GPU check:

```bash
nvidia-smi
```

## Prepare Ollama

Follow the official Ollama Linux guide, then:

```bash
sudo systemctl enable --now ollama
curl http://127.0.0.1:11434/api/tags
```

Pull models directly with Ollama. The application discovers local models but
does not pull or delete model files.

Useful small models:

```bash
ollama pull smollm2:135m
ollama pull all-minilm
```

Larger examples:

```bash
ollama pull qwen3:4b
ollama pull qwen2.5-coder:3b
ollama pull llama3.2:3b
ollama list
```

## Project Setup

```bash
cd ~/local-ai-coding-assistant
bash scripts/setup.sh
```

The script creates `.venv`, installs backend/frontend dependencies, creates
local `.env` files, and copies safe templates into `data/config/` without
overwriting existing local settings.

## Create Login Credentials

Add a local user:

```bash
.venv/bin/python scripts/manage_credentials.py set YOUR_USERNAME
```

Enter and confirm a password of at least eight characters. The script writes:

```text
data/config/credentials.json
```

The file is ordinary editable JSON:

```json
{
  "users": [
    {
      "username": "YOUR_USERNAME",
      "password_hash": "pbkdf2_sha256$..."
    }
  ]
}
```

Do not replace `password_hash` with a plaintext password. Use the management
script to generate or update hashes:

```bash
.venv/bin/python scripts/manage_credentials.py list
.venv/bin/python scripts/manage_credentials.py set ANOTHER_USER
.venv/bin/python scripts/manage_credentials.py remove OLD_USER
```

The backend rereads this file on each login.

## Start Locally

```bash
bash scripts/start.sh
```

Open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

Press `Ctrl+C` in the startup terminal to stop both development servers.

## Add and Verify the API Key

After login:

1. Open Settings from the app shell.
2. Enter a private API key.
3. Select **Save key**.
4. Select **Check** in API access.

The key is stored in two local places:

- Browser local storage, so the UI remembers it between sessions.
- `data/config/app-settings.json`, so FastAPI knows the active key.

The Account status says connected only when the browser key matches the active
backend value. For programmatic setup, `API_KEY` in `backend/.env` remains a
fallback. A key saved through the Account UI overrides that fallback.

## Per-Chat AI Settings

Open Settings and use **Conversation Settings** for the active chat. These
settings are saved with that browser-local chat and do not change other chats.

Current setting categories:

- LLM model
- Embedder model
- OCR engine
- PDF parser
- Chunker
- Vector database
- RAG pipeline
- Reranker
- Context compressor
- Vision model

Select **Refresh local models/tools** after pulling Ollama models or changing
installed parser/OCR packages. Select **Verify chat settings** for an explicit
confirmation of the active chat's selections.

New chats default to the first available LLM alphabetically. The legacy
`/models/status` and `/models/switch` endpoints still exist for compatibility,
but the main UI workflow is per-chat settings.

## PDF Parsers and OCR Detection

Python packages in `backend/requirements.txt` currently include:

```text
pymupdf
pdfplumber
ocrmypdf
```

These support detection for:

- PDF parser: `pymupdf`
- PDF parser: `pdfplumber`
- OCR engine and low-text PDF fallback: `ocrmypdf`

Tesseract is a system binary, not a Python-only package. To detect
`tesseract`, install it in the runtime where the backend actually runs. If the
backend runs in Docker, install it in the image/container, not only in a host
virtual environment.

When `ocrmypdf` is selected for a chat and the selected PDF parser returns very
little selectable text, document processing can run OCRmyPDF and extract text
from the OCR output. Other OCR engines may appear in discovery before they are
wired into document processing.

## Documents and RAG

Typical document workflow:

1. Pull a chat model and an embedding model with Ollama.
2. Save an API key.
3. Select the active chat's LLM and embedder in Conversation Settings.
4. Upload a `.txt`, `.md`, or `.pdf` document.
5. Process the document.
6. Build an index.
7. Search indexed chunks or ask a RAG-enabled chat question.

Document vectors are currently stored in local JSON files under `data/`.
Selected vector database names are recorded for future compatibility, but
external vector database backends are not wired yet.

RAG responses can include:

- source numbers
- document and chunk IDs
- vector scores
- optional rerank scores
- RAG warnings
- rerank warnings
- compression warnings and stats

## Manage Chats and Context

The browser stores up to five chats per logged-in username. Use the new-chat
button to create a chat. At five chats, the button is disabled until one is
deleted.

Each chat has isolated messages and settings. Deleting a chat removes its
browser-local record. FastAPI receives only the selected chat's recent context
with the current request.

Browser storage is application-local persistence, not guaranteed forensic disk
erasure. Clear site data in the browser when decommissioning a device.

## Local Configuration Files

`backend/.env` includes the main backend settings. Keep it ignored and local.
Common values:

```dotenv
API_KEY=
CREDENTIALS_FILE=../data/config/credentials.json
LOCAL_SETTINGS_FILE=../data/config/app-settings.json
SESSION_COOKIE_NAME=local_ai_session
SESSION_TTL_HOURS=12
SESSION_COOKIE_SECURE=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_NUM_PREDICT=768
OLLAMA_THINK=false
OLLAMA_KEEP_ALIVE=10m
CHAT_CONTEXT_MAX_CHARS=12000
CONTEXT_COMPRESSION_MAX_PROMPT_CHARS=12000
CONTEXT_COMPRESSION_RECENT_MESSAGES_TO_KEEP=10
CONTEXT_COMPRESSION_MAX_RETRIEVED_CONTEXT_CHARS=6000
CONTEXT_COMPRESSION_MAX_SUMMARY_CHARS=2000
DEFAULT_MODEL=qwen3:4b
DATA_DIRECTORY=../data
REPO_CHUNK_SIZE=2000
RAG_TOP_K=5
RAG_CANDIDATE_K=20
RAG_MAX_TOP_K=20
RERANKER_MAX_CANDIDATES=50
DOCUMENT_MAX_UPLOAD_BYTES=26214400
DOCUMENT_CHUNK_SIZE=2000
DOCUMENT_MAX_CHUNKS=500
EMBEDDING_BATCH_SIZE=16
VECTOR_STORE_BACKEND=json
```

`VECTOR_STORE_BACKEND=json` is the default and requires no extra services.
`VECTOR_STORE_BACKEND=chroma` uses the optional local Chroma adapter only when
the `chromadb` Python package is installed in the backend runtime; otherwise
the app falls back to JSON.

Login sessions are stored in memory and end when the backend restarts. Set
`SESSION_COOKIE_SECURE=true` only when the site is served over HTTPS.

## Files Intentionally Ignored by Git

Real secrets and mutable local values are excluded:

```text
.env
backend/.env
frontend/.env
data/config/credentials.json
data/config/app-settings.json
```

These safe templates are committed:

```text
.env.example
backend/.env.example
frontend/.env.example
credentials.example.json
app-settings.example.json
```

Before pushing, verify:

```bash
git status --short
git check-ignore data/config/credentials.json
git check-ignore data/config/app-settings.json
```

## Docker Compose

Prepare local files before starting containers:

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

`./data` is mounted at `/app/data`, so credentials, API settings, uploaded
documents, repository indexes, and vector indexes persist across container
replacement. Ollama continues running on the Linux host at
`127.0.0.1:11434`.

If Docker Compose complains that `backend/.env` is missing, create it from the
template:

```bash
cp backend/.env.example backend/.env
```

## Home-Network Access

By default, the production frontend uses `FRONTEND_API_BASE_URL=auto`. That
makes the browser call the backend on the same hostname or IP address used to
open the frontend. For a Linux host at `192.168.1.50`, open:

```text
http://192.168.1.50:5173
```

If `.env` already hardcodes a different `FRONTEND_API_BASE_URL`, reset it:

```dotenv
FRONTEND_API_BASE_URL=auto
```

Then rebuild once:

```bash
docker compose up --build --detach
```

HTTP does not encrypt passwords, cookies, or API keys; use an HTTPS reverse
proxy before accessing the app across an untrusted network.

For production-style deployment, review
`docs/deployment-hardening.md`, `docs/backup-restore.md`, and
`docs/release-checklist.md` before exposing the app beyond a trusted LAN.

## Tests

Default tests do not require Ollama, a GPU, downloaded models, or host data:

```bash
make test-backend
make test-frontend
make test
```

Docker tests use clean test images:

```bash
make test-backend-docker
make test-frontend-docker
make test-docker
```

Optional live Ollama smoke tests:

```bash
make setup-ollama-smoke
RUN_OLLAMA_TESTS=1 make test-ollama-smoke
```

These use tiny models to validate wiring, not response quality.

## Troubleshooting

### Login says credentials are not configured

```bash
ls -l data/config/credentials.json
.venv/bin/python scripts/manage_credentials.py list
```

### API key says not connected

Open Settings, save the key again, then check API access. The browser copy
must match `data/config/app-settings.json` or the `API_KEY` environment
fallback.

### Ollama or model discovery fails

```bash
systemctl status ollama
curl http://127.0.0.1:11434/api/tags
docker compose logs backend
df -h
```

Use `ollama list` to verify models are stored locally, then select
**Refresh local models/tools** in Settings.

### PDF parser or OCR engine is not detected

Confirm the package or binary exists in the backend runtime:

```bash
docker compose exec backend python -c "import fitz; print('pymupdf ok')"
docker compose exec backend python -c "import pdfplumber; print('pdfplumber ok')"
docker compose exec backend which ocrmypdf
docker compose exec backend which tesseract
```

If the backend runs in Docker, host virtualenv installs are not visible inside
the container.

### Port already in use

```bash
ss -ltnp | grep -E ':8000|:5173'
```

Stop the previous local process or run:

```bash
docker compose down
```
