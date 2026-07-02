<div align="center">

# Local AI Coding Assistant

**A private, self-hosted workspace for local Ollama chat, per-chat AI
configuration, document indexing, and source-grounded RAG experiments.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react&logoColor=111827)](https://react.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20Inference-111827?style=flat-square)](https://ollama.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Tests](https://img.shields.io/badge/tests-pytest%2022%20%2B%20node%205-22C55E?style=flat-square&logo=pytest&logoColor=white)](#testing)
[![License](https://img.shields.io/badge/License-MIT-7C3AED?style=flat-square)](LICENSE)

</div>

> [!IMPORTANT]
> **Continuous development:** This project is actively evolving. The current
> release is a functional portfolio-grade MVP, but interfaces, retrieval
> quality, deployment options, and tests will continue to improve.

## Overview

Local AI Coding Assistant is a full-stack application for developers who want
AI-assisted exploration without sending prompts, documents, or source code to a
cloud model provider.

The application connects a React dashboard to a FastAPI backend and a locally
installed Ollama service. Users can authenticate, manage a local API key,
maintain isolated browser-local conversations, choose AI components per chat,
upload documents, build local JSON vector indexes, retrieve source snippets,
and answer with RAG source metadata. Optional reranking and context compression
can be enabled per conversation while legacy repository keyword RAG remains
available through the API.

Internet access is required only when installing dependencies or downloading
new Ollama models. Chat prompts, generated repository indexes, credentials,
API keys, and source code remain on the host machine during normal use.

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
  attribution, optional reranking, and context compression.
- **Security-conscious configuration:** Salted password hashes, HttpOnly
  sessions, Bearer authentication, ignored secret files, and safe templates.
- **Operational readiness:** Health checks, Docker Compose, non-root backend
  execution, restart policies, setup scripts, and automated tests.

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
- Bounds chat context and model output to keep local inference responsive.

### Authentication and Account Management

- Login page backed by an editable local credentials file.
- Passwords stored as salted PBKDF2 hashes, never as plaintext.
- HttpOnly login sessions for account and model-management operations.
- Bearer API-key protection for chat and repository endpoints.
- Locally persisted API-key configuration with connection verification.
- No usernames, passwords, or API keys hardcoded in the source tree.

### Conversations

- Up to five browser-local chats per username.
- Isolated history and context for each conversation.
- Per-chat settings for LLM, embedder, OCR engine, PDF parser, chunker, vector
  database, RAG pipeline, reranker, context compressor, and vision model.
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
- Extract PDF text with PyMuPDF or pdfplumber when installed.
- Chunk documents with fixed and recursive chunking modes.
- Embed chunks with local Ollama embedding models.
- Store document chunks and vectors in a local JSON-backed index.
- Search indexed chunks without sending data to external services.
- Use retrieved chunks in chat prompts with stable source numbering and source
  metadata.
- Optionally rerank candidate chunks before prompt injection.
- Optionally compress long chat history and retrieved context before
  generation.

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
    Browser["Browser<br/>React + Vite"] -->|"Login cookie and Bearer key"| API["FastAPI API"]
    API --> Auth["Local credentials<br/>and settings"]
    API --> Components["Component registry<br/>models and tools"]
    API --> Chat["Chat orchestration"]
    API --> Documents["Document service<br/>extract and chunk"]
    Documents --> VectorIndex["Local JSON<br/>vector index"]
    VectorIndex --> Retriever["Retriever"]
    Retriever --> Reranker["Optional reranker"]
    Reranker --> Compressor["Optional context<br/>compressor"]
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
3. Protected AI requests include the configured Bearer API key.
4. Each conversation sends its own selected AI component settings.
5. Document RAG retrieves local indexed chunks when enabled for the chat.
6. Optional reranking reorders candidate chunks before prompt construction.
7. Optional context compression trims or summarizes long prompts safely.
8. The API returns the generated answer, warnings, and contributing source
   metadata.

Detailed design notes are available in
[docs/architecture.md](docs/architecture.md).

## Technology Stack

| Area | Technology | Responsibility |
| --- | --- | --- |
| Frontend | React 18, Vite 8, CSS | Authentication, chat, account settings, documents, and source UI |
| Backend | Python, FastAPI, Pydantic | APIs, validation, sessions, orchestration, and component discovery |
| Local inference | Ollama | Model downloads, text generation, embeddings, and reranker prompts |
| Retrieval | Python JSON indexes | Document vectors, source metadata, and legacy keyword RAG |
| HTTP client | HTTPX | Async communication with Ollama |
| Deployment | Docker, Docker Compose, Nginx | Reproducible frontend and backend services |
| Testing | pytest, FastAPI TestClient, Vitest, MSW | API, authentication, AI flow, documents, frontend, and Docker tests |

## Local Capability Discovery

The per-chat settings UI is backed by `GET /components/capabilities`. The
backend reuses Ollama model discovery, categorizes installed models, and also
checks for optional local tools. The response includes:

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

Optional Python packages for detection and PDF extraction are installed through
`backend/requirements.txt`:

```text
pymupdf
pdfplumber
ocrmypdf
```

Tesseract is a system binary, so Docker images or host environments must
install `tesseract-ocr` separately if you want the `tesseract` engine detected.

## Quick Start

### Prerequisites

The primary target is a Linux Mint machine with:

- Python 3.10 or newer
- Node.js 20.19+ or 22.12+
- npm
- Ollama
- Docker Engine and Docker Compose for container deployment
- An NVIDIA GPU and working driver are recommended, but not required

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

After signing in, open the account menu and create an API key. Short keys are
accepted for local testing, but a longer private key is recommended for normal
use. The application stores it only in ignored local configuration and the
current browser profile.

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

Both services should eventually report as healthy. Useful lifecycle commands:

```bash
docker compose logs --follow
docker compose restart
docker compose down
```

Detached containers continue running after the terminal or SSH session closes.
The `restart: unless-stopped` policy restarts them after a reboot once Docker
is available.

## Access from Another Computer

The application can be used from another trusted device on the same network.
Find the Linux host address:

```bash
hostname -I
```

By default, `FRONTEND_API_BASE_URL=auto` makes the browser call the backend on
the same hostname or IP address you used to open the frontend. For a host
address such as `192.168.1.50`, open:

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
2. Open the account menu and save an API key.
3. Verify the API status shows as connected.
4. Choose the active chat's model and AI settings in Conversation Settings.
5. Press **Verify chat settings** if you want an explicit confirmation.
6. Submit a prompt.

Changing a chat's model or RAG settings does not clear the conversation. Other
chats keep their own settings.

### Upload and Search Documents

Document workflows use the active chat's settings. A typical local RAG setup is:

1. Pull a small chat model and an embedding model with Ollama.
2. Select the LLM and embedder in Conversation Settings.
3. Upload a document in the workspace.
4. Build an index for that conversation.
5. Ask a question with document RAG enabled.

RAG responses include source metadata. When reranking is enabled and succeeds,
sources can include both vector and rerank scores. When context compression is
enabled, responses include compression metadata and warnings when trimming or
fallbacks occur.

OCR expansion and vision chat are not implemented yet. OCR engine discovery is
present so the UI can show which local tools are available for future phases.

### Index a Repository

For local development, enter an absolute path readable by the backend:

```text
/home/user/projects/example-repository
```

For Docker, repositories are mounted read-only beneath `/repositories`:

```text
/repositories/sample-code-repository
```

### Ask a Grounded Question

After indexing, provide the generated repository name and ask a focused
question. The response includes the source paths selected by the retriever.

## API Reference

| Method | Endpoint | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | Public | Application metadata |
| `GET` | `/health` | Public | Backend health check |
| `POST` | `/auth/login` | Credentials | Start a local session |
| `GET` | `/auth/me` | Session cookie | Return the signed-in user |
| `POST` | `/auth/logout` | Session cookie | End the session |
| `GET` | `/account/status` | Session cookie | Check account and API-key state |
| `PUT` | `/account/api-key` | Session cookie | Save a local API key |
| `GET` | `/models/status` | Session cookie | Return model and switch status |
| `POST` | `/models/switch` | Session cookie | Select an installed local model |
| `GET` | `/components/capabilities` | Session cookie | Return categorized local AI components and tools |
| `POST` | `/chat` | Bearer key | Generate a chat response |
| `POST` | `/documents/upload` | Bearer key | Stage a conversation document upload |
| `GET` | `/documents` | Bearer key | List processed documents for a conversation |
| `POST` | `/documents/{document_id}/process` | Bearer key | Extract and chunk an uploaded document |
| `POST` | `/documents/{document_id}/index` | Bearer key | Build a local JSON vector index for one document |
| `GET` | `/documents/indexes` | Bearer key | List document indexes |
| `DELETE` | `/documents/indexes/{collection_id}` | Bearer key | Delete a document vector collection |
| `POST` | `/documents/search` | Bearer key | Search indexed document chunks |
| `POST` | `/repos/index-local` | Bearer key | Index a local repository |
| `POST` | `/repos/ask` | Bearer key | Ask a grounded repository question |

### Example Chat Request

```bash
export API_KEY="your-local-api-key"

curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Explain dependency injection in FastAPI.",
    "conversationSettings":{
      "llmModel":"llama3.2:3b",
      "ragPipeline":"basic",
      "reranker":"none",
      "contextCompressor":"none"
    }
  }'
```

### Example Repository Request

The dashboard repository workspace is temporarily hidden, but the backend API
remains available:

```bash
curl -X POST http://localhost:8000/repos/index-local \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"path":"/repositories/sample-code-repository"}'

curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name":"sample-code-repository",
    "question":"Where are the calculator functions implemented?"
  }'
```

See [docs/api.md](docs/api.md) for request schemas, responses, and errors.

## Document and Repository Indexing

Document upload currently supports plain text, Markdown, and PDFs. PDF
extraction uses PyMuPDF or pdfplumber when installed in the backend runtime.
Processed chunks and embeddings are stored under ignored local data
directories.

Supported file extensions:

```text
.py .js .jsx .ts .tsx .md .json .yaml .yml .html .css
```

Ignored directories:

```text
.git node_modules .venv __pycache__ dist build
```

Legacy repository indexes are stored as readable JSON under `data/indexes/`.
Document vectors use local JSON-backed storage for the current phase. Re-
indexing a directory with the same final directory name replaces its previous
repository index.

GitHub cloning is not implemented yet. Clone a GitHub repository locally, then
index its local path.

## Configuration

Safe templates are committed for every local configuration file:

| Template | Local file | Purpose |
| --- | --- | --- |
| `.env.example` | `.env` | Docker build, LAN address, and repository mounts |
| `backend/.env.example` | `backend/.env` | Backend, Ollama, and security settings |
| `frontend/.env.example` | `frontend/.env` | Development API URL |
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
| `CONTEXT_COMPRESSION_MAX_PROMPT_CHARS` | `12000` | Prompt budget for optional compression |
| `CONTEXT_COMPRESSION_RECENT_MESSAGES_TO_KEEP` | `10` | Recent messages kept verbatim during compression |
| `CONTEXT_COMPRESSION_MAX_RETRIEVED_CONTEXT_CHARS` | `6000` | Retrieved context budget during compression |
| `CONTEXT_COMPRESSION_MAX_SUMMARY_CHARS` | `2000` | Maximum summarizer memory block length |
| `DOCUMENT_MAX_UPLOAD_BYTES` | `26214400` | Maximum uploaded document size |
| `DOCUMENT_CHUNK_SIZE` | `2000` | Target document chunk size |
| `DOCUMENT_MAX_CHUNKS` | `500` | Maximum chunks kept from one processed document |
| `EMBEDDING_BATCH_SIZE` | `16` | Maximum chunks embedded per local batch |

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
npm --prefix frontend install

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
`main`, `phase-*` branches, and pull requests. Docker verification is available
as a manual workflow so the default CI path stays fast and Ollama-free.

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
npm run test:e2e
```

See [docs/testing.md](docs/testing.md) for the full testing workflow.

## Security and Privacy

- Passwords are salted and hashed with PBKDF2.
- Login sessions are stored in backend memory and delivered through HttpOnly
  cookies.
- Protected AI routes use constant-time Bearer-key comparison.
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
|   |   |-- auth/          # Credentials, sessions, and Bearer validation
|   |   |-- rag/           # Chunking, indexing, and retrieval
|   |   |-- routers/       # FastAPI route modules
|   |   |-- schemas/       # Pydantic request and response models
|   |   `-- services/      # Ollama, model, settings, and repo services
|   |-- Dockerfile
|   `-- requirements*.txt
|-- frontend/
|   |-- src/components/    # Login, chat, account, status, and repo UI
|   |-- Dockerfile
|   `-- nginx.conf
|-- tests/                 # Isolated backend tests
|-- scripts/               # Linux setup, startup, and credential tools
|-- docs/                  # Architecture, API, and setup guides
|-- data/                  # Ignored local settings and generated indexes
|-- sample-code-repository/
|-- docker-compose.yml
`-- Makefile
```

## Current Limitations

- Document vectors are stored in local JSON files; selected vector database
  names are recorded for compatibility but external Chroma, FAISS, Qdrant, and
  LanceDB backends are not wired yet.
- Legacy repository RAG still uses keyword overlap.
- OCR engine discovery exists, and PDF OCR fallback can call supported local
  tools, but broad OCR expansion and UI workflows are still early.
- Vision model discovery exists, but vision chat is not implemented yet.
- Semantic and memory context compression modes currently fall back safely to
  implemented compressors.
- Chat responses are returned after full generation rather than streamed.
- Login sessions are in memory and end when the backend restarts.
- Browser chat persistence uses local storage on the current device.
- GitHub repositories must be cloned locally before indexing.
- The default deployment assumes a trusted home or development network.

## Roadmap

- Add real vector database backends such as Chroma, FAISS, Qdrant, or LanceDB.
- Expand OCR processing and document ingestion coverage.
- Add vision chat for local multimodal models.
- Implement semantic and memory context compression modes.
- Stream Ollama responses and model-switch events to the frontend.
- Add safe GitHub clone and update workflows.
- Introduce language-aware parsing with Tree-sitter.
- Add repository lifecycle controls and index freshness metadata.
- Add linting, test, and Docker-build checks through GitHub Actions.
- Support HTTPS deployment through a reverse proxy.

## Documentation

- [Architecture](docs/architecture.md)
- [API reference](docs/api.md)
- [Linux Mint setup](docs/setup.md)
- [Testing](docs/testing.md)
- [Development roadmap](docs/development-roadmap.md)

## Contributing

This project is under continuous development. Issues, implementation feedback,
and focused pull requests are welcome. Please avoid committing secrets,
generated indexes, local model files, or machine-specific configuration.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
