# Linux Mint Setup Guide

## Prerequisites

- Linux Mint
- Python 3.10+ with `venv`
- Node.js `20.19+` or `22.12+` with pnpm 11.9.x
- Docker Engine with the Compose plugin
- Ollama
- Git and curl
- An NVIDIA GPU is useful for larger models, but CPU-only smoke testing is
  supported with tiny models

Verify:

```bash
python3 --version
node --version
pnpm --version
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

## Frontend

The production frontend lives in `frontend/`.

```bash
make install-frontend
make run-frontend
make test-frontend
```

Open:

- Frontend: `http://localhost:5173`

Production and Docker builds set `VITE_USE_MOCK_API=false` so the app connects
to the backend. Set `VITE_USE_MOCK_API=true` only for frontend-only mock demos.

## Optional API Key for Scripts

Browser chat and local resources work after login without an API key. The
account API-key controls remain available for legacy scripts or manual API
calls that cannot use the browser session cookie.

If you need that compatibility path:

1. Open Settings from the app shell.
2. Enter a private API key.
3. Select **Save key**.
4. Select **Check** in API access.

The key is stored in two local places:

- Browser local storage, so the UI remembers it between sessions.
- `data/config/app-settings.json`, so FastAPI knows the active key.

The Account status says connected only when the browser key matches the active
backend value. This status does not block normal browser chat. For
programmatic setup, `API_KEY` in `backend/.env` remains a fallback. A key saved
through the Account UI overrides that fallback.

## Per-Chat AI Settings

Open Settings and use **Conversation Settings** for the active chat. These
settings are saved with that chat and do not change other chats. Browser
localStorage remains the default conversation store.

Current setting categories:

- LLM model
- Embedder model
- Chunker
- RAG pipeline
- Reranker
- Vision model

OCR is handled automatically. Docker installs PaddleOCR (Baidu) in the backend
image and new chats prefer it when capability discovery reports it available.
PDF parsing is handled automatically with Docling as the default parser.
Qdrant is the standard vector database and automatic context management is
always handled by the backend.
Select **Refresh local models/tools** after pulling Ollama models or changing
installed parser/OCR packages. Select **Verify chat settings** for an explicit
confirmation of the active chat's selections.

New chats default to the first available LLM alphabetically. The legacy
`/models/status` and `/models/switch` endpoints still exist for compatibility,
but the main UI workflow is per-chat settings.

## Optional Backend Conversation Persistence

By default, chats stay in the current browser profile. To store conversations
with the local backend data directory, open Settings and select **Migrate to
backend storage** in Conversation Storage.

Backend persistence:

- imports the current browser chats into `data/conversations/`
- keeps browser localStorage updated as a fallback copy
- mirrors persisted conversation metadata into the local SQLite metadata store
- is scoped to the signed-in local username
- can be turned off from Settings to return to browser-local storage
- does not provide cloud sync or multi-device sync

The backend keeps up to `CONVERSATION_MAX_COUNT` persisted conversations per
local user. The default is `50`.

## Local Metadata Store

On backend startup, the app initializes and checks a local SQLite metadata
database:

```text
data/metadata/app.sqlite3
```

The database stores a catalogue of app metadata and migration bookkeeping for
local users, mutable settings, backend-persisted conversations, document
metadata, vector collection metadata, and repository index metadata. Existing
JSON artifact files remain in place and continue to be used by the current
services. Uploaded originals, extracted text, chunks, vector payloads, and
repository index payloads are not moved into SQLite.

Run the migration command manually when diagnosing startup or backup issues:

```bash
cd backend
../.venv/bin/python -m app.metadata.cli status
../.venv/bin/python -m app.metadata.cli migrate
```

If the database is corrupt or newer than the running application supports, the
backend stops with an actionable migration error instead of continuing with an
unknown metadata state. If non-critical document or index metadata artifacts
are unreadable, migration skips those records with warnings and leaves the
original files unchanged.

## PDF Parsers and OCR Detection

Python packages in `backend/requirements.txt` currently include:

```text
pymupdf
pdfplumber
docling
ocrmypdf
paddleocr
paddlepaddle
```

These support detection for:

- Automatic PDF parser: `docling`
- Compatibility PDF parser fallback: `pymupdf`
- Compatibility PDF parser fallback: `pdfplumber`
- Automatic OCR engine and low-text PDF fallback: `paddleocr`
- Compatibility OCR fallback: `ocrmypdf`

Tesseract is a system binary, not a Python-only package. To detect
`tesseract`, install it in the runtime where the backend actually runs. If the
backend runs in Docker, install it in the image/container, not only in a host
virtual environment.

Document processing prefers Docling for PDFs because it produces AI-friendly
Markdown from document structure. If Docling is unavailable or fails, the
backend can fall back to PyMuPDF/pdfplumber for older saved settings and direct
API compatibility. When a parser returns very little selectable text,
processing can run PaddleOCR and extract text from rendered PDF pages. The UI no
longer asks users to choose between PDF parsers or OCR engines.

## Documents and RAG

Typical document workflow:

1. Pull a chat model and an embedding model with Ollama.
2. Select the active chat's LLM and embedder in Conversation Settings.
3. Upload a `.txt`, `.md`, `.pdf`, `.docx`, `.html`, `.htm`, `.csv`, or
   `.tsv` document.
4. Process the document.
5. Build an index.
6. Search indexed chunks or ask a RAG-enabled chat question.

The UI runs document processing and indexing through small local background
jobs so it can show progress. The original synchronous document API endpoints
remain available for scripts and tests.

Document uploads are sniffed before processing so obvious extension/content
mismatches fail early with clear errors. DOCX, HTML, CSV, and TSV extraction
uses lightweight local parsers. OCR is automatic for scanned or low-text PDFs
when PaddleOCR is available, and missing optional compatibility tools do not
break the default document flow.

Document vectors use Qdrant as the standard vector database. Docker Compose
starts Qdrant alongside the backend and stores data in the named
`qdrant_storage` volume, so indexed vectors survive container recreation and
ordinary `docker compose down` runs. A small JSON vector store remains as an
internal test/emergency fallback when the Qdrant client is unavailable, but the
UI no longer asks users to choose a vector database.

Conversational memory also uses Qdrant, but it is stored in a separate
collection from document and repository vectors. The default collection is
`local_ai_conversation_memory_v1`. Only durable memories such as preferences,
decisions, constraints, unresolved tasks, and important project facts are
stored; ordinary chat text is skipped. Because memory uses the same persistent
Qdrant service and `qdrant_storage` volume, it survives container recreation
and ordinary `docker compose down` runs.

RAG responses can include:

- source numbers
- document and chunk IDs
- vector scores
- optional rerank scores
- RAG warnings
- rerank warnings
- compression warnings and stats

## Manage Chats and Context

The browser stores up to five chats per logged-in username by default. Use the
new-chat button to create a chat. At five chats, the button is disabled until
one is deleted.

Each chat has isolated messages and settings. Deleting a chat removes its
browser-local record and, when backend persistence is active, removes the
backend-persisted record too. FastAPI receives only the selected chat's recent
context with the current request.

Browser storage is application-local persistence, not guaranteed forensic disk
erasure. Clear site data in the browser when decommissioning a device.
Backend-persisted conversations are stored under `data/conversations/`.

## Local Configuration Files

`backend/.env` includes the main backend settings. Keep it ignored and local.
Common values:

```dotenv
API_KEY=
CREDENTIALS_FILE=../data/config/credentials.json
LOCAL_SETTINGS_FILE=../data/config/app-settings.json
SESSION_COOKIE_NAME=local_ai_session
CSRF_COOKIE_NAME=local_ai_csrf
CSRF_HEADER_NAME=x-csrf-token
SESSION_TTL_HOURS=12
SESSION_COOKIE_SECURE=false
SESSION_SIGNING_KEY=
LOGIN_RATE_LIMIT_ATTEMPTS=5
LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
LOGIN_LOCKOUT_SECONDS=300
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
REPOSITORY_ALLOWED_ROOTS=
REPO_CHUNK_SIZE=2000
RAG_TOP_K=5
RAG_CANDIDATE_K=20
RAG_MAX_TOP_K=20
RERANKER_MAX_CANDIDATES=50
DOCUMENT_MAX_UPLOAD_BYTES=26214400
DOCUMENT_CHUNK_SIZE=2000
DOCUMENT_MAX_CHUNKS=500
EMBEDDING_BATCH_SIZE=16
VECTOR_STORE_BACKEND=qdrant
QDRANT_URL=
QDRANT_API_KEY=
CONVERSATION_MAX_COUNT=50
METADATA_DATABASE_FILE=
```

`VECTOR_STORE_BACKEND=qdrant` is the default. In Docker Compose,
`QDRANT_URL=http://qdrant:6333` is set automatically for the backend. For
non-Docker development, leave `QDRANT_URL` empty to use qdrant-client local
path mode under `data/vector_indexes/qdrant`, or point it at a local Qdrant
service.

`REPOSITORY_ALLOWED_ROOTS` is optional. When empty, the backend allows
repository indexing from the project root, the configured data directory, and
`/repositories` for Docker mounts. Set it to a comma-separated list of trusted
absolute paths when you want to index repositories from another local folder.
Repository indexes include freshness fingerprints and return warnings when
files change after indexing. Repository vector indexing is opt-in through the
`/repos/index-local/vector` endpoint and uses separate vector collections from
document RAG.

Repository source parsing does not require extra parser packages. The backend
uses Python's standard-library AST for Python and conservative lightweight
heuristics for JS/TS, Markdown, JSON/YAML, HTML, and CSS. Parser failures fall
back to line-based chunks so indexing can continue.

Check backend availability with:

```bash
curl -H "Authorization: Bearer $API_KEY" \
  http://localhost:8000/vectorstores/health
```

The vector API can export/import portable collection payloads and migrate a
collection from JSON to an available adapter. If the requested target backend
is unavailable, the operation falls back to JSON and reports that fallback in
the response.

Login sessions are stored in memory by default and end when the backend
restarts. Set `SESSION_SIGNING_KEY` to a long random local secret when you want
session cookies to remain valid across backend restarts. Keep that value out of
Git and back it up with other local secrets.

Cookie-authenticated unsafe requests use a double-submit CSRF token. The
backend sets an HttpOnly session cookie and a readable `CSRF_COOKIE_NAME`
cookie; the frontend sends that value in `CSRF_HEADER_NAME`. Login attempts are
rate-limited by username and client address with the `LOGIN_*` settings.

Set `SESSION_COOKIE_SECURE=true` only when the site is served over HTTPS.

## Files Intentionally Ignored by Git

Real secrets and mutable local values are excluded:

```text
.env
backend/.env
frontend/.env
data/config/credentials.json
data/config/app-settings.json
data/conversations/
data/metadata/
data/uploads/
data/vector_indexes/
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

For a production-style local host, use the safer template:

```bash
python3 scripts/validate_env.py
docker compose -f docker-compose.prod.yml up --build --detach
```

`docker-compose.prod.yml` binds the frontend to `127.0.0.1:5173` by default,
keeps the backend on host networking for local Ollama access, mounts
repositories read-only, and does not expose Ollama. Set
`FRONTEND_BIND_ADDRESS` only when a trusted reverse proxy or LAN exposure is
intentional.

`./data` is mounted at `/app/data`, so credentials, API settings, uploaded
documents, backend-persisted conversations, the SQLite metadata database,
repository indexes, and vector indexes persist across container replacement.
Ollama continues running on the Linux host at
`127.0.0.1:11434`.

If Docker Compose complains that `backend/.env` is missing, create it from the
template:

```bash
cp backend/.env.example backend/.env
```

## Home-Network Access

By default, the production frontend uses `FRONTEND_API_BASE_URL=auto`. That
makes the browser use same-origin API calls, while the frontend Nginx container
proxies backend routes such as `/auth/login`, `/chat`, `/documents`, and
`/repos` to FastAPI. For a Linux host at `192.168.1.50`, open:

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

Before replacing containers on a production-style install, run the upgrade
helper. It validates local env files and creates a zip archive of `data/`
before any Compose replacement:

```bash
python3 scripts/upgrade.py
python3 scripts/upgrade.py --apply
```

The first command is a dry run that stops after backup. The `--apply` form runs
Docker Compose only after validation and backup succeed.

HTTP does not encrypt passwords, cookies, or API keys; use an HTTPS reverse
proxy before accessing the app across an untrusted network.

For production-style deployment, review
`docs/deployment-hardening.md` and `docs/backup-restore.md` before exposing
the app beyond a trusted LAN.

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

The API key is optional for normal browser use. A disconnected API-key status
only matters for scripts or manual API calls that use `Authorization: Bearer`.
If you use that compatibility path, open Settings, save the key again, then
check API access. The browser copy must match `data/config/app-settings.json`
or the `API_KEY` environment fallback.

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
