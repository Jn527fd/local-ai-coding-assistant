# Architecture

## Overview

Local AI Coding Assistant is a self-hosted React and FastAPI application for
local Ollama chat, per-conversation AI configuration, document indexing, and
source-grounded RAG. It keeps prompts, uploaded documents, generated indexes,
credentials, and settings on the local machine.

```text
Browser
  |
  v
React frontend
  |
  | JSON / multipart HTTP
  | HttpOnly login cookie + Authorization: Bearer <API_KEY>
  v
FastAPI backend
  |-----------------------------|--------------------------|
  v                             v                          v
Ollama service             Document service          Legacy repo RAG
  |                             |                          |
  | /api/tags                   v                          v
  | /api/generate        uploads / chunks JSON       repository JSON indexes
  | /api/embed                  |
  v                             v
component registry        JSON vector store
                                |
                                v
                      retrieval -> optional rerank
                                |
                                v
                     optional context compression
                                |
                                v
                          final chat prompt
```

The current production storage model is deliberately local and inspectable.
Operational payloads remain in JSON files under `data/`, while
`data/metadata/app.sqlite3` stores a small SQLite catalogue for metadata and
migration bookkeeping. This is not a large-scale vector database, cloud sync
system, or multi-user persistence layer.

## Frontend

The frontend is a React single-page application built by Vite.

```text
frontend/src/
|-- App.jsx                 # Main state container
|-- api.js                  # Fetch helpers and error handling
|-- apiBase.js              # Runtime API base URL resolution
|-- chatState.js            # Browser-local chat/settings fallback state
|-- main.jsx
|-- styles.css
`-- components/
    |-- AccountPanel.jsx    # API key, capabilities, per-chat settings
    |-- Conversation.jsx
    |-- NavigationRail.jsx
    |-- Workspace.jsx
    |-- WorkspaceSidebar.jsx
    `-- ...
```

`App.jsx` currently owns most application state: authentication, API key,
capabilities, chats, active chat settings, document lists, indexes, search
results, chat sending, dialogs, and toasts. This is functional but large; a
future roadmap phase should extract focused hooks.

Conversation storage behavior:

- Up to five chats per username are stored in local storage.
- Each chat stores its own `settings` object.
- Browser localStorage remains the default and fallback store.
- Users can opt into backend JSON persistence from Settings.
- Backend-persisted conversations live under `data/conversations/`, scoped by
  the signed-in local username.
- New chat defaults are built from discovered capabilities.
- The frontend sends the active chat's recent history and settings with each
  request.

The Account panel no longer switches one global UI model as the main workflow.
It exposes Conversation Settings for the active chat and a verification button
so users can confirm which settings are selected. When the backend provides
capability execution metadata, each selected setting also shows a compact
status line such as implemented, fallback, detected but not wired, planned, or
unavailable.

## Backend Application

`backend/app/main.py` exposes an application factory. It loads settings,
configures CORS and logging, creates services, stores them on `app.state`, and
registers routers.

```text
backend/app/
|-- main.py
|-- config.py
|-- metadata/
|   |-- cli.py
|   |-- migrations.py
|   `-- store.py
|-- auth/
|-- routers/
|   |-- auth.py
|   |-- account.py
|   |-- models.py
|   |-- components.py
|   |-- conversations.py
|   |-- documents.py
|   |-- chat.py
|   |-- repos.py
|   `-- health.py
|-- schemas/
|-- services/
|   |-- component_registry.py
|   |-- conversation_service.py
|   |-- document_service.py
|   |-- local_settings_service.py
|   |-- model_manager.py
|   |-- ollama_service.py
|   `-- repo_service.py
|-- ai/
|   |-- components.py
|   |-- execution_context.py
|   |-- chunkers/
|   |-- ocr/
|   |-- parsers/
|   |-- embedders/
|   |-- rerankers/
|   |-- compressors/
|   |-- pipelines/
|   `-- vectorstores/
`-- rag/                    # Legacy repository keyword RAG
```

Pydantic models validate request bodies. Blocking file work runs in
Starlette's thread pool where needed.

## Local Metadata Store

`backend/app/metadata/store.py` owns the local SQLite catalogue. The initial
schema includes:

- `schema_migrations`
- `users`
- `settings`
- `conversations`
- `documents`
- `vector_collections`
- `repository_indexes`
- `jobs`

`backend/app/metadata/migrations.py` runs forward-only startup migrations.
Fresh installs create the database automatically. Existing JSON metadata is
imported conservatively from credentials, local settings, backend conversation
stores, document metadata artifacts, vector collection metadata artifacts, and
repository JSON indexes. The original JSON files remain in place and continue
to back the current runtime services.

Conversation writes from `ConversationPersistenceService` are mirrored into
SQLite so the catalogue remains current after the initial migration. Uploaded
files, extracted text, chunk payloads, vector embeddings, and repository index
payloads remain in their existing artifact stores.

`JobService` also persists local runtime job metadata in SQLite. Job execution
is still in-process and local; there is no external queue, Redis, Celery, or
remote worker.

Manual migration diagnostics are available with:

```bash
cd backend
../.venv/bin/python -m app.metadata.cli status
../.venv/bin/python -m app.metadata.cli migrate
```

If the SQLite database is corrupt or newer than the running application
supports, startup fails with a migration error. Non-critical unreadable
document or index metadata is skipped with warnings so existing list/get
fallback behavior is preserved.

## Authentication

The browser login flow verifies salted PBKDF2 hashes from the ignored
credentials file and creates a random, in-memory session. The session token is
sent in an HttpOnly SameSite=Lax cookie.

Session-protected endpoints:

- `/auth/me`
- `/auth/logout`
- `/account/*`
- `/models/*`
- `/components/*`

Bearer-protected endpoints:

- `/chat`
- `/documents/*`
- `/repos/*`

The expected Bearer key comes from ignored `data/config/app-settings.json`,
with `API_KEY` as a fallback. `hmac.compare_digest` performs the comparison.

This auth model is intended for one operator or a trusted local network. It is
not a public multi-tenant security model.

## Ollama and Component Discovery

`OllamaService` is the backend boundary around Ollama HTTP calls. It handles:

- `GET /api/tags`
- `POST /api/generate`
- embedding endpoints used by the embedder provider

`ComponentRegistry` reuses Ollama model discovery and categorizes local
models into:

- LLMs
- embedders
- rerankers
- vision models
- unknown Ollama models

It also checks local Python packages and binaries for OCR engines and PDF
parsers. Static categories such as chunkers, vector databases, RAG pipelines,
and context compressors are returned so the frontend can present consistent
settings. Some static choices are compatibility placeholders or fallback modes
rather than fully implemented execution paths.

Each capability entry includes explicit execution metadata:

- `implementationStatus` and `implemented` for quick UI decisions.
- `execution.status`, `execution.mode`, and `execution.description` for
  user-facing explanation.
- Package or binary `checks` for local tools.

This metadata is additive. Existing runtime resolution still uses `available`
and the selected capability ID, so the enriched contract does not change chat,
document, RAG, reranking, or compression behavior by itself.

## AI Service and Provider Boundaries

`backend/app/services/*` owns application workflows, persistence, validation,
and external service clients. `backend/app/ai/*` owns narrow component
interfaces and adapters that can be swapped in tests or future providers.

`backend/app/ai/components.py` defines runtime-checkable protocol boundaries
for:

- LLM generation
- embedding
- OCR
- PDF parsing
- chunking
- vector stores
- retrieval
- reranking
- context compression
- RAG pipelines

Real adapters include the Ollama LLM, embedding, and reranking providers, the
document retrieval pipeline, token/summarizer compression, and the local JSON
vector store. Packages named `unavailable.py` are explicit non-executing
adapters. They preserve dependency-injection seams for capabilities that are
discoverable or planned, but they raise `ComponentNotImplementedError` with a
clear adapter-boundary message when called. They are not active runtime
implementations.

## AI Execution Context

`AISettingsResolver` combines the active conversation settings, component
registry data, and legacy active model fallback into a resolved execution
context. Chat, document processing, indexing, and search use this resolved
context to decide which LLM, embedder, parser, chunker, vector database,
pipeline, reranker, and compressor should be used.

The resolver is the main boundary between frontend settings and backend
execution. It allows invalid or unavailable choices to produce controlled
warnings or validation errors instead of crashing.

## Document Pipeline

Document flow:

```text
POST /documents/upload
  -> validate conversationId, extension, content signature, and size
  -> detect duplicate content within the conversation
  -> store original file under data/uploads/<conversation>/<document>
  -> write metadata.json

POST /documents/{document_id}/process
  -> resolve conversation settings
  -> extract text from .txt, .md, .pdf, .docx, .html, .csv, or .tsv
  -> chunk text with fixed or recursive chunking
  -> write extracted.json, chunks.json, metadata.json

POST /documents/{document_id}/index
  -> require valid embedderModel
  -> embed chunks through Ollama
  -> upsert vectors into local JSON vector store
```

The synchronous document endpoints remain available. The frontend uses
`POST /documents/{document_id}/process/jobs` and
`POST /documents/{document_id}/index/jobs` for minimal progress feedback, then
polls `/jobs/{job_id}` until the job succeeds, fails, or is cancelled.
Cancellation is conservative and only checked before or between safe steps.

The document service validates conversation IDs, document IDs, upload
extensions, file signatures, upload size, artifact paths, and metadata
identity. Missing or corrupt metadata is returned as failed document metadata
instead of crashing list/get calls. Missing originals fail processing with
`404`, empty extracted text fails processing with a clear error, malformed
chunk artifacts are not indexed, and duplicate uploads reuse existing document
metadata.

PDF text extraction supports PyMuPDF and pdfplumber when installed in the
backend runtime. Docling is discoverable but not implemented for parsing yet.
DOCX, HTML, CSV, and TSV extraction uses conservative Python standard-library
parsers. Extraction diagnostics such as parser name, text length, line counts,
row counts, and paragraph counts are preserved in document metadata where
available.
When selected and available, OCRmyPDF is used as a fallback for PDFs whose
parser output has too little selectable text. OCR warnings and resolved engine
metadata are preserved in document metadata. Other OCR engines remain
discoverable until provider adapters are added.

## Vector Store Adapter Layer

`VectorStoreManager` selects the active vector backend and reports adapter
health. `JsonVectorStore` remains the default backend and stores vectors under
`DATA_DIRECTORY/vector_indexes`. Collections are scoped by conversation,
embedder model, and selected vector database name.

Search computes cosine similarity in Python and returns the top results. This
is excellent for transparent local testing and small document sets. It is not
intended to replace Chroma, FAISS, Qdrant, or LanceDB for large collections.

`ChromaVectorStore` is the first optional real backend adapter. It is only
available when the `chromadb` Python package is installed and
`VECTOR_STORE_BACKEND=chroma` is configured. If Chroma is not installed or the
backend is left at the default `json`, document indexing and RAG continue to
use the JSON store. Component discovery exposes adapter health and JSON
fallback metadata for vector database settings.

## Chat, RAG, Reranking, and Compression

Chat flow:

```text
POST /chat or /chat/stream
  -> authenticate Bearer key
  -> resolve conversation settings
  -> optionally retrieve document chunks
  -> optionally rerank candidates
  -> optionally compress history/context
  -> build final prompt
  -> generate or stream with Ollama text or vision model
  -> return answer or SSE events with warnings, sources, rerank metadata, compression metadata
```

Document RAG retrieves local vector-indexed chunks when the selected pipeline
requires retrieval or request `ragOptions` enables it. Sources include stable
source numbers, vector scores, optional rerank scores, final rank, and text
previews.

Source metadata is normalized before prompt injection and response payloads are
created. Empty retrieved chunks are skipped with a warning. Missing source
fields fall back to safe labels such as `Document`, `unknown-document`, or a
derived chunk ID. Long display fields and previews are truncated with an
explicit `[truncated]` marker. After reranking or compression removes context,
the remaining sources are renumbered so `[Source N]` in the prompt matches the
returned `sources[N-1]` metadata.

Reranking uses an Ollama generation prompt that asks the selected reranker
model for a numeric relevance score. This avoids assuming a native Ollama
rerank endpoint. Failures fall back to vector-ranked order with warnings.

Compression modes:

- `none`: unchanged prompt behavior.
- `token`: deterministic trimming.
- `summarizer`: LLM summary of older history.
- `semantic`: currently falls back to token compression.
- `memory`: currently falls back to summarizer or token compression.

Image-bearing chat requests validate base64 PNG, JPEG, or WebP attachments and
use the selected `visionModel` instead of the text `llmModel`. Text-only chat
continues through the existing LLM path. `/chat` remains a complete JSON
response endpoint. `/chat/stream` emits `progress`, `metadata`, `token`,
`done`, and `error` server-sent events so the browser can render partial
assistant messages while preserving the non-streaming fallback contract.

## Legacy Repository RAG

Repository indexing remains available through `/repos/index-local` and
`/repos/ask`.

```text
POST /repos/index-local
  -> validate directory
  -> recursively discover supported source files
  -> split text into line-aware chunks
  -> write data/indexes/<safe-name>.json

POST /repos/ask
  -> load repository JSON index
  -> keyword score chunks
  -> build guarded prompt
  -> generate with Ollama
```

This path uses keyword overlap, not embeddings. It is intentionally preserved
while document RAG evolves separately.

## Container Deployment

```text
Browser
  |-- :5173 -> Nginx frontend container
  `-- :8000 -> FastAPI backend container (Linux host network)
                                      |
                                      v
                              host Ollama :11434

Host ./data              <-> /app/data
Host LOCAL_REPOS_ROOT     -> /repositories (read-only)
```

The backend image uses Python 3.12 and runs as a non-root user whose UID can
match the host user. The frontend uses a Node build stage followed by an
Nginx runtime stage. Both services define health checks and use
`restart: unless-stopped`.

Linux host networking lets the backend reach Ollama on
`127.0.0.1:11434` without exposing Ollama to the LAN. Repository mounts are
read-only; generated data is written through the `data/` mount.

`VITE_API_BASE_URL=auto` is compiled into the frontend by default. At runtime
the browser resolves it to the same hostname or IP address used to open the
frontend, with port `8000` for FastAPI.

## Testing

Default tests are hermetic:

- Backend pytest uses temporary local config and fake/mocked Ollama behavior.
- Frontend tests use Vitest, Testing Library, MSW, and axe.
- Docker test images are built from committed dependency files.
- Optional live Ollama tests are skipped unless `RUN_OLLAMA_TESTS=1`.

Important commands:

```bash
make test-backend
make test-frontend
make test-docker
make smoke-docker
```

The CPU-friendly live Ollama smoke profile is opt-in:

```bash
make setup-ollama-smoke
RUN_OLLAMA_TESTS=1 make test-ollama-smoke
```

## Trust Boundary and Limits

The application is intended for one operator on a trusted machine or home
network. Current limits include:

- one shared API key
- in-memory login sessions
- browser-local chat persistence by default with optional backend JSON
  persistence mirrored into the local metadata catalogue
- streaming is implemented for chat generation but not every long-running
  document operation
- JSON vector storage
- discovery-only or fallback-only component options
- vision chat depends on locally pulled multimodal Ollama models
- OCR execution is limited to OCRmyPDF PDF fallback
- no public-internet hardening
