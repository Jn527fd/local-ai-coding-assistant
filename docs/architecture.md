# Architecture

## Overview

Local AI Coding Assistant is a self-hosted React and FastAPI application. It
uses Ollama for local text generation and stores repository indexes as JSON.
The current retrieval strategy is intentionally simple and explainable:
question keywords are compared with indexed code and file paths before the
best chunks are placed into a grounded prompt.

```text
Browser
  |
  v
React frontend
  |
  | JSON over HTTP
  | HttpOnly login cookie + Authorization: Bearer <API_KEY>
  v
FastAPI backend
  |--------------------------|
  v                          v
Ollama /api/generate   Repository service
                              |
                              v
                    JSON indexes + retriever
```

## Frontend

The frontend is a React single-page application built by Vite.

```text
frontend/src/
|-- App.jsx
|-- api.js
|-- main.jsx
|-- styles.css
`-- components/
    |-- ChatBox.jsx
    |-- LoginPage.jsx
    |-- AccountPanel.jsx
    |-- RepoIndexer.jsx
    `-- StatusPanel.jsx
```

`App.jsx` restores the HttpOnly login session and owns the browser copy of the
API key. The key is persisted in local storage and passed to protected
AI/repository requests. `api.js` centralizes cookies, the Bearer header, JSON
parsing, network errors, and FastAPI error extraction.

The components provide:

- Public backend health checks
- Local login and logout
- Account/API-key settings and connection checks
- Allowlisted model switching with progress
- Direct chat with the active Ollama model
- Five username-scoped local chats with isolated context and deletion
- Local repository indexing
- Repository questions and source-path display

For production, Vite builds static assets that Nginx serves from the frontend
container.

## Backend

`backend/app/main.py` exposes an application factory. It loads settings,
configures CORS and startup logging, stores settings on `app.state`, and
registers the health, chat, and repository routers.

```text
backend/app/
|-- main.py
|-- config.py
|-- auth/
|   |-- api_key.py
|   |-- credentials.py
|   |-- session.py
|   `-- user_session.py
|-- routers/
|   |-- auth.py
|   |-- account.py
|   |-- models.py
|   |-- health.py
|   |-- chat.py
|   `-- repos.py
|-- schemas/
|-- services/
|   |-- local_settings_service.py
|   |-- model_manager.py
|   |-- ollama_service.py
|   `-- repo_service.py
`-- rag/
    |-- chunker.py
    |-- indexer.py
    `-- retriever.py
```

Pydantic request and response models validate all JSON payloads. Blocking
filesystem indexing and index loading run in Starlette's thread pool so they
do not block the async request loop.

## Authentication

The browser login flow verifies salted PBKDF2 hashes from the ignored
credentials file and creates a random, in-memory session. The session token is
sent only in an HttpOnly SameSite=Lax cookie. Account and model-management
routes require this session.

`GET /` and `GET /health` are public. The `/chat` and `/repos` routers retain
Bearer API-key protection for programmatic and UI requests.

```text
Authorization: Bearer <API_KEY>
              |
              v
HTTPBearer -> constant-time comparison -> route handler
```

The expected key comes from ignored `data/config/app-settings.json`, with
`API_KEY` as a fallback. `hmac.compare_digest` performs the comparison.

The local login and shared API key are suitable for a private, trusted
deployment. They are not a replacement for multi-user roles, TLS, or rate
limiting.

## Ollama Integration

`OllamaService` is the only backend component that knows Ollama's HTTP API.
It sends a non-streaming request to:

```text
POST <OLLAMA_BASE_URL>/api/generate
```

The service translates connection failures, timeouts, upstream HTTP failures,
invalid JSON, and empty model responses into application-specific exceptions.
Routers map those exceptions to clear `502`, `503`, or `504` responses.

FastAPI dependency injection creates the service from active settings. Tests
replace that dependency with a fake, so the test suite never calls a real
model.

## Model Management

`ModelManager` derives the selectable catalog from Ollama's `/api/tags`
response. It parses `details.parameter_size`, excludes models above the
configured 7B ceiling or with unknown metadata, and persists the selected
installed model name. There is no model-name allowlist and the application
does not download or delete model files.

One async lock prevents concurrent switches, and generation endpoints return
`409` while model state is changing. Mutable state is persisted in ignored
`data/config/app-settings.json`.

## Chat Context Lifecycle

The frontend stores at most five chats per username in browser local storage.
FastAPI is stateless: a chat request contains the current message plus up to 30
recent messages from only the selected chat. The router formats that explicit
history into the prompt sent to Ollama. It keeps the newest history that fits
the configured total-character budget, preventing accumulated assistant
answers from producing an unbounded prompt. Ollama generation also uses a
configurable output-token limit and disables extended thinking by default.
The conversation is independent of the active model, so its retained history
is passed to the next selected model.

Deleting a chat removes its local-storage record. Because neither FastAPI nor
Ollama receives a server-side conversation identifier or stores chat history,
that deleted chat is absent from all future context.

## Repository Indexing

The indexing request flow is:

```text
POST /repos/index-local
  -> authenticate
  -> resolve and validate directory
  -> recursively discover supported files
  -> prune ignored directories
  -> read UTF-8 text
  -> split into line-aware chunks
  -> atomically write data/indexes/<safe-name>.json
```

Supported source and documentation formats are `.py`, `.js`, `.jsx`, `.ts`,
`.tsx`, `.md`, `.json`, `.yaml`, `.yml`, `.html`, and `.css`. The indexer
ignores `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, and `build`.

Each JSON index contains:

```json
{
  "version": 1,
  "repo_name": "example",
  "source_path": "/absolute/path/example",
  "indexed_at": "UTC timestamp",
  "files": ["relative/path.py"],
  "chunks": [
    {
      "id": "relative/path.py:1",
      "file_path": "relative/path.py",
      "start_line": 1,
      "end_line": 40,
      "content": "..."
    }
  ],
  "skipped_files": []
}
```

The service writes a temporary file and replaces the destination only after a
complete JSON serialization, reducing the chance of a partial index.

## RAG Flow

Repository questions use retrieval-augmented generation:

```text
POST /repos/ask
  -> authenticate
  -> load repository JSON index
  -> normalize question terms
  -> score content and file-path overlap
  -> choose up to RAG_TOP_K chunks
  -> build a guarded prompt with paths and line ranges
  -> generate with the active size-approved local model through Ollama
  -> return answer and unique source paths
```

The tokenizer splits prose, `snake_case`, and `camelCase`, removes common stop
words, and compares unique terms. Content matches score one point; file-path
matches receive a two-point bonus. Zero-overlap chunks are excluded.

The prompt instructs the model to use only supplied repository context, treat
code and comments as untrusted data rather than instructions, and state when
the available context is insufficient.

Keyword retrieval is transparent and dependency-light, but it cannot reliably
match synonyms or concepts that use different words. Embeddings are the
natural next retrieval upgrade.

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
match the Linux host user. The frontend uses a Node build stage followed by a
small Nginx runtime stage. Both services define health checks and use
`restart: unless-stopped`.

Linux host networking lets the backend reach Ollama on
`127.0.0.1:11434` without exposing Ollama to the LAN. Repository mounts are
read-only; only generated indexes are written through the `data/` mount.

`VITE_API_BASE_URL=auto` is compiled into the frontend during its Docker build
by default. At runtime the browser resolves that value to the same hostname or
IP address used to open the frontend, with port `8000` for FastAPI. Explicit
non-loopback API URLs are still supported for custom deployments.

## Testing

Pytest creates a fresh FastAPI application with:

- A fixed test-only API key
- A temporary data directory
- An Ollama URL that is never contacted
- A dependency-injected fake Ollama service for chat

The current suite covers public health, missing/invalid authentication, and a
successful mocked chat request. Frontend `node:test` coverage checks LAN API
host resolution and login session-cookie verification. The tests run without
Docker, network access, or Ollama.

## Trust Boundary and Limits

The application is intended for one operator on a trusted machine or home
network. An authenticated caller can request indexing of directories readable
by the backend process. For Docker deployments, the read-only repository mount
provides a useful filesystem boundary.

Current limits include one shared API key, non-streaming generation,
keyword-only retrieval, JSON storage, local-path indexing only, and no
multi-user isolation.
