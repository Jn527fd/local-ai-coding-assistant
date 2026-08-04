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
  | HttpOnly login cookie + CSRF token
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
component registry        Qdrant vector store
                                |
                                v
                      retrieval -> optional rerank
                                |
                                v
                     automatic context management
                                |
                                v
                          final chat prompt
                                ^
                                |
                    separate Qdrant memory collection
```

The current production storage model is deliberately local and inspectable.
Operational payloads remain in JSON files under `data/`, while
`data/metadata/app.sqlite3` stores a small SQLite catalogue for metadata and
migration bookkeeping. This is not a large-scale vector database, cloud sync
system, or multi-user persistence layer.

## Frontend

The production frontend is a React single-page application built by Vite from
`frontend/`. It is the only frontend shipped with the repository.

```text
frontend/src/
|-- App.tsx
|-- api/          # HTTP client helpers
|-- auth/         # Session and protected-route state
|-- components/   # Shared UI primitives
|-- domain/       # Typed app models, DTOs, and defaults
|-- features/     # Chat, settings, sources, profile, and configuration UI
|-- routes/       # Route declarations and route guards
|-- services/     # Mock and HTTP service adapters
`-- test/         # Frontend test utilities
```

`App.tsx` owns the conversation-page shell and delegates workflow behavior to
feature modules and the `appServices` facade. UI code does not call `fetch`
directly for app workflows; `frontend/src/services/` selects mock or HTTP
adapters behind typed service contracts. HTTP mode is the production path, while
mock mode remains available for hermetic frontend tests and local UI work.

Accessibility conventions are handled in the component layer. Long-running
frontend states use polite status regions, failures use alert regions where
appropriate, source citations remain keyboard-addressable buttons grouped as a
source list, and shared dialogs focus their first actionable control when
opened. Mobile layout rules favor wrapping long filenames, source labels, and
document search controls instead of clipping them.

Conversation storage behavior:

- Up to five chats per username are stored in local storage.
- Each chat stores its own `settings` object.
- Browser localStorage remains the default and fallback store.
- Users can opt into backend JSON persistence from Settings.
- Backend-persisted conversations live under `data/conversations/`, scoped by
  the signed-in local username.
- New chat defaults are built from discovered capabilities.
- The frontend sends the active chat's recent history, settings, and saved
  system prompt with each request. System prompt file import fills that per-chat
  prompt rather than creating or pulling an Ollama model.

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
credentials file and creates a random session. By default sessions are
in-memory and end when the backend restarts. Operators can set
`SESSION_SIGNING_KEY` to sign session cookies so they remain valid across a
backend restart. The session token is sent in an HttpOnly SameSite=Lax cookie.

Unsafe session-cookie requests require a matching CSRF header and readable CSRF
cookie. The React API helper mirrors the `local_ai_csrf` cookie into
`X-CSRF-Token` for POST, PUT, PATCH, and DELETE requests. Login attempts are
rate-limited in memory by username and client address. Auth and settings
changes emit redacted audit log events that include action, username, client,
and success/failure without passwords or API-key values.

The backend adds conservative response headers on all routes:
`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and
`Permissions-Policy`.

Diagnostics endpoints are session-protected, still accept legacy Bearer keys,
and are intentionally metadata-only. They summarize runtime, model, document,
retrieval, vector, and job state
without prompts, chat messages, document/OCR contents, secrets, session values,
CSRF values, cookies, or private file paths. The support bundle endpoint wraps
the same redacted data for local troubleshooting and should still be reviewed
before sharing.

Session-protected endpoints:

- `/auth/me`
- `/auth/logout`
- `/account/*`
- `/models/*`
- `/components/*`
- `/chat`
- `/documents/*`
- `/repos/*`
- `/jobs/*`
- `/vectorstores/*`
- `/diagnostics/*`

Legacy Bearer-compatible endpoints:

- `/chat`
- `/documents/*`
- `/repos/*`
- `/jobs/*`
- `/vectorstores/*`
- `/diagnostics/*`

The expected optional Bearer key comes from ignored
`data/config/app-settings.json`, with `API_KEY` as a fallback.
`hmac.compare_digest` performs the comparison when that compatibility path is
used.

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
- context management
- RAG pipelines

Real adapters include the Ollama LLM, embedding, and reranking providers, the
document retrieval pipeline, automatic context manager, and the Qdrant vector
store. Packages named `unavailable.py` are explicit non-executing
adapters. They preserve dependency-injection seams for capabilities that are
discoverable or planned, but they raise `ComponentNotImplementedError` with a
clear adapter-boundary message when called. They are not active runtime
implementations.

## AI Execution Context

`AISettingsResolver` combines the active conversation settings, component
registry data, and legacy active model fallback into a resolved execution
context. Chat, document processing, indexing, and search use this resolved
context to decide which LLM, embedder, parser, chunker, vector database,
pipeline, and reranker should be used.

The resolver is the main boundary between frontend settings and backend
execution. It resolves older context-compressor settings to automatic mode for
compatibility and allows invalid or unavailable choices to produce controlled
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

PDF text extraction prefers Docling when installed in the backend runtime,
because it converts PDFs into AI-friendly structured Markdown. PyMuPDF and
pdfplumber remain available as compatibility fallbacks for older saved settings
and direct API calls. DOCX, HTML, CSV, and TSV extraction uses conservative
Python standard-library parsers. Extraction diagnostics such as parser name,
text length, line counts, row counts, and paragraph counts are preserved in
document metadata where available.
When available, PaddleOCR is the preferred automatic fallback for PDFs whose
parser output has too little selectable text. OCRmyPDF remains registered for
older saved settings and direct API compatibility. OCR warnings and resolved
engine metadata are preserved in document metadata.

## Vector Store Adapter Layer

`VectorStoreManager` selects the active vector backend and reports adapter
health. `QdrantVectorStore` is the standard backend for document and repository
vectors. Docker Compose runs Qdrant as a local service and persists its storage
in the named `qdrant_storage` volume. For non-Docker local development,
qdrant-client can also run in local path mode under
`DATA_DIRECTORY/vector_indexes/qdrant` when `QDRANT_URL` is empty. Collections
are scoped by conversation, embedder model, and vector database name.

`JsonVectorStore` remains as an internal test/emergency fallback when
qdrant-client is unavailable. `ChromaVectorStore` remains in the adapter layer
for legacy migration/export compatibility but is no longer exposed as a
user-selectable vector database.

The vector store contract includes collection upsert, query, metadata listing,
deletion, health, and portable export/import operations. The
`/vectorstores/health` endpoint reports the configured backend, active backend,
fallback state, and adapter checks. `/vectorstores/collections/export`,
`/vectorstores/collections/import`, and `/vectorstores/collections/migrate`
use the portable JSON collection payload to support local backup and
JSON-to-adapter migration. LanceDB remains deferred.

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

Retrieval quality evaluation lives outside the request path in
`app.evaluation.retrieval`. It runs deterministic fake-provider cases against
a small fixture corpus and measures recall, best rank, source accuracy,
warning behavior, and source metadata shape. The harness is intended to catch
retrieval/source regressions before algorithm tuning; live model quality
evaluation remains opt-in only.

Context management is automatic. The chat request path preserves recent
messages and the latest user message verbatim, maintains a structured note
when older messages are omitted, retrieves long-term source context through the
document/repository vector pipeline, applies reranked source order when
available, trims deterministically against the configured prompt budget, and
uses structured LLM evidence extraction only if the deterministic pass still
cannot fit retrieved context. Extracted evidence must be an exact substring of
the source passage, so code, identifiers, paths, numbers, and names are not
accepted if the model paraphrases them. Evidence extraction failures or drift
fall back to deterministic trimming with warnings.

Durable conversational memory is intentionally separate from document and
repository RAG. `ConversationMemoryService` stores preferences, decisions,
constraints, unresolved tasks, and important project facts in the dedicated
Qdrant collection `local_ai_conversation_memory_v1` by default. Each memory
contains workspace, conversation, timestamp, type, importance, and
source-message metadata. Prompt assembly retrieves relevant memories before
automatic context management so they are budgeted with history and source
context. Duplicate prevention uses a stable hash over workspace,
conversation, type, and normalized memory text.

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
  -> split text into language-aware symbol chunks when practical
  -> fall back to line-aware chunks when parsing fails
  -> record file fingerprints for freshness checks
  -> write data/indexes/<safe-name>.json

POST /repos/ask
  -> load repository JSON index
  -> compare freshness metadata with current files
  -> keyword score chunks
  -> build guarded prompt
  -> generate with Ollama

POST /repos/index-local/vector
  -> run the same local repository indexer
  -> resolve the selected embedder/vector backend
  -> embed repository chunks into a sourceType=repository collection

POST /repos/search-vector
  -> search only sourceType=repository vector collections
  -> return file path, line range, score, and freshness warnings
```

The legacy ask path still uses keyword overlap, not embeddings. Repository
vector indexing is explicit opt-in and stores separate collections so existing
document search/RAG does not start returning code chunks accidentally.
Repository paths must resolve inside configured trusted roots. Git clone/update
automation remains later roadmap work.

Language-aware parsing is intentionally lightweight. Python uses the standard
library AST. JS/TS, Markdown, JSON/YAML, HTML, and CSS use conservative
standard-library or regex heuristics. Chunks preserve file path, language, line
range, and optional symbol metadata. Existing version-1 repository indexes
remain readable because repository retrieval treats metadata as optional.

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

The backend and frontend share the private Compose network. The backend reaches
host Ollama through `host.docker.internal:11434` without publishing Ollama to
the LAN. Repository mounts are read-only; generated data is written through the
`data/` mount.

`VITE_API_BASE_URL=auto` is compiled into the Docker frontend by default. The
frontend normalizes `auto` to same-origin API calls, and the Nginx runtime
proxies backend routes to FastAPI through the private Compose service name
`backend:8000`.

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
- OCR execution is limited to low-text PDF fallback
- no public-internet hardening
