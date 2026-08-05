<div align="center">

# Local AI Coding Assistant

**A private local AI workspace for Ollama chat, document RAG, source
citations, and per-chat model/tool settings.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=111827)](https://react.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Inference-111827?style=flat-square)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![CI](https://github.com/Jn527fd/local-ai-coding-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Jn527fd/local-ai-coding-assistant/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-MIT-7C3AED?style=flat-square)](LICENSE)

</div>

> [!IMPORTANT]
> **Public preview:** This is a functional local-first application, not a
> hosted SaaS or public multi-tenant service. It is designed for one operator
> on a trusted machine or private network.

## Overview

Local AI Coding Assistant is a full-stack app for developers who want useful
AI assistance without sending prompts, documents, or source code to a cloud
model provider.

The application connects a React dashboard to a FastAPI backend and a locally
installed Ollama service. You can sign in locally, choose AI components per
chat, upload documents, build local vector indexes, retrieve source snippets,
stream answers, inspect source metadata, and enable optional reranking while
automatic context management keeps long chats and retrieved context within the
active model budget.

Internet access is required only when installing dependencies or downloading
new Ollama models. Chat prompts, generated repository indexes, credentials,
API keys, and source code remain on the host machine during normal use.

## Highlights

- Local Ollama chat with streaming responses and per-chat model selection.
- Document upload, PDF/text extraction, chunking, embeddings, search, and RAG.
- Source-grounded answers with source numbers, vector scores, rerank scores,
  warnings, and compression metadata.
- Local capability discovery for LLMs, embedders, rerankers, vision models,
  chunkers, RAG pipelines, and runtime context-management support.
- Automatic Docling PDF extraction, PaddleOCR fallback for low-text PDFs, and
  structured vision evidence handoff for local multimodal Ollama models.
- Docker Compose deployment, hermetic default tests, optional live Ollama smoke
  tests, and release-readiness documentation.

## Quick Links

| Need | Start here |
| --- | --- |
| Install and run locally | [Quick Start](#quick-start) |
| Understand the design | [Architecture](#architecture) and [docs/architecture.md](docs/architecture.md) |
| Review API behavior | [API Reference](#api-reference) and [docs/api.md](docs/api.md) |
| Run tests | [Testing](#testing) and [docs/testing.md](docs/testing.md) |
| Deploy safely | [Security and Privacy](#security-and-privacy) and [docs/deployment-hardening.md](docs/deployment-hardening.md) |
| Report issues or contribute | [Contributing](#contributing) and [docs/support.md](docs/support.md) |

## Application Preview

### Local Login

![Local AI Coding Assistant login page](docs/assets/login-preview.png)

### Developer Dashboard

![Local AI Coding Assistant dashboard](docs/assets/dashboard-preview.png)

## Why This Project

This project demonstrates more than a basic LLM chat interface:

- **Full-stack engineering:** React/Vite frontend, FastAPI backend, typed
  request schemas, documented APIs, and containerized deployment.
- **Local AI integration:** Ollama model discovery, capability categorization,
  text generation, embeddings, and optional reranker adapters with no cloud LLM
  dependency.
- **Retrieval-augmented generation:** Document upload, extraction, chunking,
  local JSON vector indexing, retrieval-only search, RAG chat, source
  attribution, optional reranking, and automatic context management.
- **Security-conscious configuration:** Salted password hashes, HttpOnly
  sessions, optional legacy Bearer keys for scripts, ignored secret files, and
  safe templates.
- **Operational readiness:** Health checks, Docker Compose, non-root backend
  execution, restart policies, setup scripts, SQLite metadata migrations, and
  automated tests.

## Features

### Private Local AI

- Runs inference through Ollama on the host machine.
- Discovers locally installed Ollama models and categorizes LLMs, embedders,
  rerankers, vision models, and unknown models.
- Detects local OCR engines and PDF parsers when their Python packages or
  binaries are installed in the backend runtime.
- Keeps model selection per conversation instead of relying on one global UI
  switcher.
- Displays connection state, local model/tool inventory, and user-facing
  errors.
- Supports image attachments through a structured vision-evidence step: the
  selected vision model extracts text, paths, code, UI details, observations,
  and uncertainties, while the primary chat model writes the answer.
- Bounds chat context and model output to keep local inference responsive.

### Authentication and Account Management

- Login page backed by an editable local credentials file.
- Passwords stored as salted PBKDF2 hashes, never as plaintext.
- HttpOnly login sessions for account, chat, document, repository, diagnostics,
  and model-management operations.
- Optional legacy Bearer API-key support for scripts and manual API calls.
- Locally persisted API-key configuration remains available for compatibility.
- No usernames, passwords, or API keys hardcoded in the source tree.

### Conversations

- Up to five browser-local chats per username by default.
- Optional backend conversation persistence stores chats in local JSON files
  under `data/conversations/` after the user opts in from Settings.
- A local SQLite metadata catalogue under `data/metadata/` records migrated
  users, settings, conversations, document metadata, and index metadata while
  preserving the JSON artifact stores.
- Isolated history and context for each conversation.
- Per-chat settings for LLM, embedder, chunker, RAG pipeline, reranker, and
  vision model.
- Compact setting status lines show whether a selected capability is
  implemented, fallback-backed, detected but not wired, planned, or
  unavailable when that metadata is available.
- A visible verification button confirms the active chat's selected settings.
- New chats default to the first available LLM alphabetically.
- Complete chat deletion so removed messages are excluded from future prompts.
- A maximum of 30 recent messages per request, further bounded by a backend
  context-size limit.

### Documents and RAG

- Upload and process local documents through the backend.
- Show local job progress while processing and indexing documents.
- Support text, Markdown, PDF, DOCX, HTML, CSV, and TSV uploads with safe
  file-type sniffing before processing.
- Extract PDF text with Docling by default, with PyMuPDF/pdfplumber retained as
  backend compatibility fallbacks.
- Run PaddleOCR automatically as a low-text/scanned PDF fallback.
- Record extraction diagnostics and detect duplicate document uploads.
- Chunk documents with fixed and recursive chunking modes.
- Embed chunks with local Ollama embedding models.
- Store document chunks and vectors in Qdrant.
- Search indexed chunks without sending data to external services.
- Use retrieved chunks in chat prompts with stable source numbering and source
  metadata.
- Optionally rerank candidate chunks before prompt injection.
- Automatically manage long chat history, durable memories, image evidence,
  and retrieved context before generation.

### Repository Intelligence

- Legacy repository indexing remains available through the backend API.
- Recursive indexing of local code repositories.
- Support for Python, JavaScript, TypeScript, React, Markdown, JSON, YAML,
  HTML, and CSS.
- Automatic exclusion of generated or dependency-heavy directories such as
  `.git`, `node_modules`, `.venv`, `dist`, and `build`.
- Human-readable JSON indexes with file paths and source line ranges.
- Keyword-overlap retrieval for transparent, dependency-light RAG.
- Grounded answers that return the source file paths used as context.

### Deployment and Developer Experience

- Dockerfiles for the FastAPI backend and production Nginx frontend.
- Docker Compose health checks and detached deployment.
- Linux setup and startup scripts.
- OpenAPI documentation at `/docs`.
- Dependency-injected pytest coverage that does not require Ollama or Docker.
- LAN access for trusted devices on the same home network.

## Architecture

```mermaid
flowchart LR
    Browser["Browser<br/>React + Vite"] -->|"Login cookie"| API["FastAPI API"]
    API --> Auth["Local credentials<br/>and settings"]
    API --> Components["Component registry<br/>models and tools"]
    API --> Chat["Chat orchestration"]
    API --> Documents["Document service<br/>extract and chunk"]
    Documents --> VectorIndex["Local vector<br/>index"]
    VectorIndex --> Retriever["Retriever"]
    Retriever --> Reranker["Optional reranker"]
    Reranker --> Compressor["Automatic context<br/>manager"]
    Chat --> Compressor
    Compressor --> Prompt["Final prompt"]
    Components --> Ollama["Ollama on host"]
    Prompt --> Ollama
    API --> RepoIndexer["Legacy repository<br/>keyword RAG"]
    Ollama --> API
```

### Request Flow

1. The user signs in with credentials stored in an ignored local JSON file.
2. The browser receives an HttpOnly session cookie for account controls.
3. Protected browser requests use the login session cookie and CSRF token.
4. Each conversation sends its own selected AI component settings.
5. Document RAG retrieves local indexed chunks when enabled for the chat.
6. Optional reranking reorders candidate chunks before prompt construction.
7. Automatic context management preserves recent messages and trims or
   extracts source evidence only when the prompt budget requires it.
8. The API returns the generated answer, warnings, and contributing source
   metadata.

Detailed design notes are available in
[docs/architecture.md](docs/architecture.md).

## Technology Stack

| Area | Technology | Responsibility |
| --- | --- | --- |
| Frontend | React 19, Vite 8, TypeScript, CSS | Authentication, chat, account settings, documents, and source UI |
| Backend | Python, FastAPI, Pydantic | APIs, validation, sessions, orchestration, and component discovery |
| Local inference | Ollama | Model downloads, text generation, embeddings, and reranker prompts |
| Metadata | SQLite + local JSON artifacts | Migration bookkeeping and local metadata catalogue |
| Retrieval | Qdrant + internal JSON fallback | Document, repository, and memory vectors plus legacy keyword RAG |
| HTTP client | HTTPX | Async communication with Ollama |
| Deployment | Docker, Docker Compose, Nginx | Reproducible frontend and backend services |
| Testing | pytest, FastAPI TestClient, Vitest, MSW | API, authentication, AI flow, documents, frontend, and Docker tests |

## Local Capability Discovery

The per-chat settings UI is backed by `GET /components/capabilities`. The
backend reuses Ollama model discovery, categorizes installed models, and also
reports backend-managed document and context components. The response includes:

- `llmModels`
- `embedderModels`
- `rerankerModels`
- `visionModels`
- `ocrEngines`
- `pdfParsers`
- `chunkers`
- `vectorDatabases`
- `ragPipelines`
- `contextCompressors`
- `unknownOllamaModels`

Every installed model Ollama reports can appear automatically. The application
does not download or delete model files. You decide which models are
appropriate for your hardware by pulling them directly with Ollama.

Pull any suitable models directly with Ollama:

```bash
ollama pull qwen3:4b
ollama pull qwen2.5-coder:3b
ollama pull llama3.2:3b
ollama list
```

While Account is open, the Ollama status refreshes periodically; the
**Refresh local models/tools** button refreshes the capability inventory
immediately. Model and tool selection requires no internet connection after
installation. To reclaim disk space manually, use `ollama rm MODEL_NAME`.

Python packages for PDF extraction and OCR are installed through
`backend/requirements.txt`:

```text
docling
paddleocr
paddlepaddle
```

Docling is the default PDF parser for AI-friendly document extraction.
PaddleOCR is the default OCR fallback for scanned or low-text PDFs. PyMuPDF,
pdfplumber, and OCRmyPDF remain backend compatibility fallbacks for older saved
settings and direct API calls.

The standard vector backend is Qdrant. Docker Compose starts a Qdrant service
with a named `qdrant_storage` volume so indexed vectors survive container
recreation and ordinary `docker compose down` runs.

Do not use `docker compose down -v` unless you intentionally want to delete
Qdrant data. The `-v` flag removes the named volume that stores document,
repository, and conversational memory vectors.

Tesseract is no longer part of the main UI workflow. If older saved settings or
direct API calls reference it, detection still requires installing the
`tesseract-ocr` system binary in the backend runtime.

## Quick Start

### Prerequisites

The primary setup path targets Linux Mint or another modern Linux host with:

- Python 3.10 or newer
- Node.js 20.19+ or 22.12+
- pnpm 11.9.x
- Ollama
- Docker Engine and Docker Compose for container deployment
- An NVIDIA GPU and working driver are recommended, but not required

Windows users can run the app through WSL or Docker, but the setup scripts and
examples in this README are written for a Linux shell. See
[docs/setup.md](docs/setup.md) for the fuller environment notes.

Verify optional NVIDIA acceleration:

```bash
nvidia-smi
```

Install Ollama using the
[official Linux instructions](https://docs.ollama.com/linux), then pull the
default model:

```bash
ollama pull qwen3:4b
curl http://127.0.0.1:11434/api/tags
```

### Local Development

From the repository root:

```bash
bash scripts/setup.sh
.venv/bin/python scripts/manage_credentials.py set YOUR_USERNAME
bash scripts/start.sh
```

Open:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`

After signing in, browser chat and local resource access work with the login
session. The account API-key controls remain only for legacy scripts or manual
API calls that cannot use the browser session cookie.

Press `Ctrl+C` in the startup terminal to stop both development servers.

### Docker Compose

Ollama remains installed on the Linux host. Compose runs the frontend and
backend:

```bash
cp .env.example .env
cp backend/.env.example backend/.env
mkdir -p data/config
cp credentials.example.json data/config/credentials.json
cp app-settings.example.json data/config/app-settings.json
python3 scripts/manage_credentials.py set YOUR_USERNAME
sed -i "s/^APP_UID=.*/APP_UID=$(id -u)/" .env

docker compose up --build --detach
docker compose ps
```

For production-style local hosting, validate env files and use the safer
template that binds the frontend to localhost by default:

```bash
python3 scripts/validate_env.py
docker compose -f docker-compose.prod.yml up --build --detach
```

Before replacing containers, run `python3 scripts/upgrade.py` to create a
pre-upgrade `data/` backup, then rerun with `--apply` when ready.

Both services should eventually report as healthy. Useful lifecycle commands:

```bash
docker compose logs --follow
docker compose restart
docker compose down
```

`docker compose down` keeps the named Qdrant volume. `docker compose down -v`
is destructive and deletes `qdrant_storage`, including indexed document,
repository, and conversational memory vectors.

Detached containers continue running after the terminal or SSH session closes.
The `restart: unless-stopped` policy restarts them after a reboot once Docker
is available.

## Access from Another Computer

The application can be used from another trusted device on the same network.
Find the Linux host address:

```bash
hostname -I
```

By default, `FRONTEND_API_BASE_URL=auto` makes the Docker frontend use
same-origin API calls. Nginx proxies backend routes such as `/auth/login`,
`/chat`, `/documents`, and `/repos` to FastAPI, so the browser only needs the
frontend URL. For a host address such as `192.168.1.50`, open:

```text
http://192.168.1.50:5173
```

If you previously hardcoded `FRONTEND_API_BASE_URL` in `.env`, either remove
that override or set it back to:

```dotenv
FRONTEND_API_BASE_URL=auto
```

Then rebuild the frontend once:

```bash
docker compose up --build --detach
```

> [!WARNING]
> This is a trusted-network application. Do not expose ports `5173`, `8000`,
> or `11434` directly to the public internet.

## Using the Application

### Chat with a Model

1. Sign in with a configured local user.
2. Choose the active chat's model and AI settings in Conversation Settings.
3. Press **Verify chat settings** if you want an explicit confirmation.
4. Submit a prompt.

Changing a chat's model or RAG settings does not clear the conversation. Other
chats keep their own settings.

The Context / System Prompt panel can import a UTF-8 text file. Imported
content fills the active chat's system prompt and is sent with that chat's
requests so it can guide the model's responses. It does not pull, create, or
replace local Ollama models.

### Upload and Search Documents

Document workflows use the active chat's settings. A typical local RAG setup is:

1. Pull a small chat model and an embedding model with Ollama.
2. Select the LLM and embedder in Conversation Settings.
3. Upload a document in the workspace.
4. Build an index for that conversation.
5. Ask a question with document RAG enabled.

RAG responses include source metadata. When reranking is enabled and succeeds,
sources can include both vector and rerank scores. Automatic context
management preserves recent messages verbatim, keeps source attribution
stable, trims retrieved context deterministically, and reports compression
metadata or warnings when the model budget requires it.

Image attachments are analyzed by the selected vision model before final
prompt assembly. The analysis is stored as a structured artifact for the
conversation, then relevant image evidence can be reused in later turns. The
primary LLM remains the only model that produces user-facing answers.

OCR is automatic for scanned or low-text PDFs. Docker installs PaddleOCR
(Baidu) for CPU-friendly local OCR, and OCRmyPDF remains available as a
compatibility fallback for older saved settings or API calls. Image evidence
works when a local multimodal Ollama model is selected for the active chat.

### Index a Repository

For local development, enter an absolute path readable by the backend:

```text
/home/user/projects/example-repository
```

For Docker, repositories are mounted read-only beneath `/repositories`:

```text
/repositories/example-repository
```

### Ask a Grounded Question

After indexing, provide the generated repository name and ask a focused
question. The response includes the source paths selected by the retriever.

## API Reference

The backend exposes documented FastAPI routes for:

- authentication and local account state
- model status and component capability discovery
- complete and streaming chat responses
- optional backend conversation persistence, migration, import, and export
- document upload, processing, indexing, search, and index deletion
- local repository indexing and grounded repository questions
- health checks and application metadata

OpenAPI documentation is available at `/docs` when the backend is running.
See [docs/api.md](docs/api.md) for endpoint details, request schemas,
response examples, and error behavior.

## Document and Repository Indexing

Document upload currently supports plain text, Markdown, PDF, DOCX, HTML,
CSV, and TSV files. Uploads are sniffed before processing so obvious
extension/content mismatches fail with clear errors. PDF extraction uses
Docling by default when installed in the backend runtime, with PyMuPDF and
pdfplumber retained as compatibility fallbacks. Processed chunks,
extraction diagnostics, and embeddings are stored under ignored local data
directories. Duplicate uploads in the same conversation reuse existing
document metadata instead of storing another copy.

Supported file extensions:

```text
.py .js .jsx .ts .tsx .md .json .yaml .yml .html .css
```

Ignored directories:

```text
.git node_modules .venv __pycache__ dist build
```

Legacy repository indexes are stored as readable JSON under `data/indexes/`.
Repository indexes include a local file fingerprint; repository answers and
vector searches warn when the source files have changed since the last index.
Local repository paths must be inside configured roots. By default, the backend
allows the project root, the configured data directory, and `/repositories` for
Docker mounts. Set `REPOSITORY_ALLOWED_ROOTS` to a comma-separated list for
other trusted local folders.

Repository vector indexing is available as an explicit opt-in through
`/repos/index-local/vector` and `/repos/search-vector`. It reuses the selected
embedder and vector backend, stores collections separately from document
collections, and does not change legacy `/repos/index-local` or `/repos/ask`
keyword behavior.

Repository chunks use lightweight language-aware parsing for Python, JS/TS,
Markdown, JSON/YAML, HTML, and CSS. Source citations and vector metadata can
include language, symbol kind, and symbol name. If a parser cannot understand a
file, indexing falls back to safe line-based chunks.

Document and repository vectors use Qdrant as the standard backend. Docker
Compose persists Qdrant data in the named `qdrant_storage` volume, while a
small JSON store remains as an internal test/emergency fallback when the Qdrant
client is unavailable. Vector backend health diagnostics are available from
`/vectorstores/health`, and collection export/import/migration endpoints can
copy portable vector payloads between available stores. Re-indexing a directory
with the same final directory name replaces its previous repository index.

Conversational memory is stored in a separate Qdrant collection, but it uses
the same persistent `qdrant_storage` volume. It survives ordinary container
replacement and `docker compose down`; it is deleted by `docker compose down
-v` unless you have exported the volume first.

GitHub cloning is not implemented yet. Clone a GitHub repository locally, then
index its local path.

## Configuration

Safe templates are committed for every local configuration file:

| Template | Local file | Purpose |
| --- | --- | --- |
| `.env.example` | `.env` | Docker build, LAN address, and repository mounts |
| `backend/.env.example` | `backend/.env` | Backend, Ollama, and security settings |
| `frontend/.env.example` | `frontend/.env` | Development API URL and mock-mode switch |
| `credentials.example.json` | `data/config/credentials.json` | Local users and password hashes |
| `app-settings.example.json` | `data/config/app-settings.json` | Active API key and legacy model fallback |

Important inference settings:

| Variable | Default | Purpose |
| --- | ---: | --- |
| `OLLAMA_TIMEOUT_SECONDS` | `120` | Generation request timeout |
| `OLLAMA_NUM_PREDICT` | `768` | Maximum generated tokens |
| `OLLAMA_THINK` | `false` | Enable supported models' extended thinking |
| `OLLAMA_KEEP_ALIVE` | `10m` | Keep the active model loaded between requests |
| `CHAT_CONTEXT_MAX_CHARS` | `12000` | Bound conversation context size |
| `RAG_TOP_K` | `5` | Maximum retrieved chunks added to a RAG prompt |
| `RAG_CANDIDATE_K` | `20` | Default candidate chunks fetched before reranking |
| `RAG_MAX_TOP_K` | `20` | Hard cap for requested RAG result count |
| `RERANKER_MAX_CANDIDATES` | `50` | Hard cap for reranker candidate scoring |
| `CONTEXT_COMPRESSION_MAX_PROMPT_CHARS` | `12000` | Prompt budget for automatic context management |
| `CONTEXT_COMPRESSION_RECENT_MESSAGES_TO_KEEP` | `10` | Recent messages kept verbatim during compression |
| `CONTEXT_COMPRESSION_MAX_RETRIEVED_CONTEXT_CHARS` | `6000` | Retrieved context budget during compression |
| `CONTEXT_COMPRESSION_MAX_SUMMARY_CHARS` | `2000` | Maximum compatibility summary block length |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `26214400` | Maximum uploaded document size |
| `DOCUMENT_CHUNK_SIZE` | `2000` | Target document chunk size |
| `DOCUMENT_MAX_CHUNKS` | `500` | Maximum chunks kept from one processed document |
| `EMBEDDING_BATCH_SIZE` | `16` | Maximum chunks embedded per local batch |
| `VECTOR_STORE_BACKEND` | `qdrant` | Active vector backend |
| `QDRANT_URL` | empty | Optional Qdrant service URL; Docker sets this to `http://qdrant:6333` |
| `QDRANT_API_KEY` | empty | Optional Qdrant API key for protected deployments |
| `MEMORY_COLLECTION_NAME` | `local_ai_conversation_memory_v1` | Separate Qdrant collection for durable conversational memories |
| `MEMORY_TOP_K` | `5` | Maximum long-term memories retrieved during prompt assembly |
| `MEMORY_MIN_IMPORTANCE` | `0.35` | Minimum memory importance for auto-store and retrieval |
| `MEMORY_AUTO_STORE_ENABLED` | `true` | Enable conservative automatic storage of durable user-provided memories |
| `CONVERSATION_MAX_COUNT` | `50` | Maximum backend-persisted conversations per local user |
| `METADATA_DATABASE_FILE` | empty | Optional override for the local SQLite metadata database |

Real `.env`, credentials, application settings, generated indexes, virtual
environments, dependencies, and build output are excluded by `.gitignore`.
The backend test suite includes a repository hygiene check that fails if an
ignored local artifact becomes tracked.

## Testing

The default test path is hermetic. Backend tests use temporary local
configuration and mocked Ollama clients; frontend unit tests use MSW handlers;
browser tests can boot `tests/fakes/fake_ollama.py`. No default test requires
Ollama, a GPU, downloaded models, host data, or network access.

```bash
python -m pip install -r requirements-dev.txt
pnpm --dir frontend install --frozen-lockfile

make test-backend
make test-frontend
make test
```

Dockerized checks build clean test images from the committed dependency files:

```bash
make test-backend-docker
make test-frontend-docker
make test-docker
```

GitHub Actions runs backend pytest and frontend lint/test/build on pushes to
`main`, the development branch `testing_main`, and pull requests. Docker
verification is available as a manual workflow so the default CI path stays
fast and Ollama-free.

Quick smoke checks are also available:

```bash
make smoke
make smoke-docker
```

Live Ollama tests are opt-in and skipped by default. They never run unless
`RUN_OLLAMA_TESTS=1` is set:

```bash
RUN_OLLAMA_TESTS=1 make test-ollama
OLLAMA_TEST_MODEL=qwen3:4b RUN_OLLAMA_TESTS=1 make test-ollama
```

CPU-friendly live app-flow smoke tests are also opt-in. They use tiny models
only to validate wiring on a CPU laptop:

```bash
make setup-ollama-smoke
RUN_OLLAMA_TESTS=1 make test-ollama-smoke
```

The default smoke models are `smollm2:135m` for chat and `all-minilm` for
embeddings. Set `PULL_RERANKER=1` only if you also want to pull the optional
reranker smoke model.

Playwright tests remain separate from the default frontend CI script:

```bash
cd frontend
pnpm test:e2e
```

See [docs/testing.md](docs/testing.md) for the full testing workflow.
Retrieval quality regression coverage uses a small fake-provider corpus in
`tests/fixtures/retrieval_eval/`; it is deterministic and does not require
Ollama.

## Manual Local Smoke

Use this path when you want to run the frontend against the real local backend:

```bash
python -m pip install -r requirements-dev.txt
pnpm --dir frontend install --frozen-lockfile

copy backend\.env.example backend\.env
python scripts\manage_credentials.py set YOUR_USERNAME

make run-backend
make run-frontend
```

Open `http://localhost:5173`, sign in, refresh local models/tools, send a
short chat, upload a small text document, process/index it, and ask a RAG
question that cites the document source.

Docker users can run the promoted production frontend and backend with:

```bash
copy backend\.env.example backend\.env
docker compose up --build
```

Then open `http://localhost:5173`.

Before a remote deployment, also review the
[deployment hardening guide](docs/deployment-hardening.md),
[backup and restore guide](docs/backup-restore.md), and
[dependency and security review](docs/dependency-security.md).

## Security and Privacy

- Passwords are salted and hashed with PBKDF2.
- Login sessions are stored in backend memory and delivered through HttpOnly
  cookies.
- Protected browser routes require a valid login session and CSRF token.
- Legacy Bearer-key authentication remains available for scripts and manual
  API calls.
- Secrets and mutable configuration are stored only in ignored local files.
- Repository mounts are read-only in the default Docker configuration.
- Logs include operational metadata, not prompts, passwords, or API keys.
- Model switching rejects names that are not installed in local Ollama.

This project is designed for a trusted local network, not as a hardened
internet-facing multi-tenant service. Review the
[current limitations](#current-limitations) before broader deployment.

## Project Structure

```text
local-ai-coding-assistant/
|-- backend/
|   |-- app/
|   |   |-- ai/            # Providers, embedders, rerankers, compressors, and vector stores
|   |   |-- auth/          # Credentials, sessions, and Bearer validation
|   |   |-- rag/           # Legacy repository chunking, indexing, and retrieval
|   |   |-- routers/       # FastAPI route modules
|   |   |-- schemas/       # Pydantic request and response models
|   |   `-- services/      # Documents, Ollama, settings, models, and repositories
|   |-- Dockerfile
|   `-- requirements*.txt
|-- frontend/
|   |-- src/               # Production React/Vite frontend
|   |-- Dockerfile
|   `-- nginx.conf
|-- tests/                 # Isolated backend tests
|-- scripts/               # Linux setup, startup, and credential tools
|-- docs/                  # Architecture, API, and setup guides
|-- data/                  # Ignored local settings, metadata, and generated indexes
|-- docker-compose.yml
`-- Makefile
```

## Current Limitations

- Document and repository vectors now standardize on Qdrant. The JSON vector
  store remains only as an internal fallback when Qdrant client support is
  unavailable.
- Legacy repository RAG still uses keyword overlap.
- OCRmyPDF fallback exists for low-text PDFs, but broad OCR expansion and UI
  workflows are still early.
- Vision chat requires a local multimodal Ollama model and is not part of the
  default tiny smoke-model setup.
- Context management is automatic. Legacy `contextCompressor` request values
  are accepted for compatibility but are not user-selectable.
- Chat streaming is implemented for generation; broader runtime progress for
  every long-running operation is still limited.
- Login sessions are in memory and end when the backend restarts.
- Browser chat persistence uses local storage by default. Backend JSON
  persistence is opt-in, local to this installation, and mirrored into the
  SQLite metadata catalogue.
- GitHub repositories must be cloned locally before indexing.
- The default deployment assumes a trusted home or development network.

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Linux Mint setup](docs/setup.md)
- [Testing](docs/testing.md)
- [Deployment hardening](docs/deployment-hardening.md)
- [Backup and restore](docs/backup-restore.md)
- [Dependency and security review](docs/dependency-security.md)
- [Support and hotfix guidance](docs/support.md)
- [Security policy](SECURITY.md)
- [Changelog](CHANGELOG.md)
- [Release notes: 0.2.0 stable v2](docs/release-notes-0.2.0.md)

## Contributing

This project is under continuous development. Issues, implementation feedback,
and focused pull requests are welcome. Please avoid committing secrets,
generated indexes, local model files, or machine-specific configuration.
For issue triage and hotfix expectations, see
[docs/support.md](docs/support.md).

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
