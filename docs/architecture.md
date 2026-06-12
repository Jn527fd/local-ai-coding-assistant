# Architecture

## Status

Phase 6 implements the FastAPI application boundary, environment-backed
configuration, Bearer API key authentication, local Ollama text generation,
JSON-based repository indexing, and keyword-based RAG.

## Planned Components

- **Frontend:** React and Vite interface for health status, chat, repository
  indexing, and repository questions.
- **Backend:** FastAPI application that exposes health, chat, and repository
  endpoints. The application factory in `backend/app/main.py` owns startup,
  middleware, and router registration.
- **Configuration:** `backend/app/config.py` reads environment variables and an
  optional backend `.env` file using Pydantic Settings.
- **Authentication:** `backend/app/auth/api_key.py` validates the
  `Authorization: Bearer <API_KEY>` header against the environment-backed
  secret using a constant-time comparison.
- **LLM provider:** `backend/app/services/ollama_service.py` sends
  non-streaming requests to Ollama's `/api/generate` endpoint.
- **Repository index:** `backend/app/rag/indexer.py` discovers supported files,
  while `backend/app/rag/chunker.py` creates line-aware text chunks.
- **Repository service:** `backend/app/services/repo_service.py` validates
  paths and atomically stores one JSON index per repository under
  `data/indexes/`.
- **Retriever:** `backend/app/rag/retriever.py` normalizes prose and code
  identifiers, ranks chunks by keyword overlap, and builds a guarded prompt.
- **RAG flow:** Load an existing index, retrieve relevant chunks, add them to a
  grounded prompt, send the prompt to Ollama, and return source paths.

## Planned Request Flow

```text
User -> React UI -> FastAPI -> Authentication
                              |-> Ollama
                              `-> Repository index -> Retriever -> Ollama
```

Implementation details and design decisions will be added in later phases.

## Current Backend Flow

```text
Request -> CORS middleware -> FastAPI router -> API key dependency
                                              -> Ollama service
                                              -> Pydantic response validation
```

The `/` and `/health` endpoints are intentionally public. The `/chat` router
and the complete `/repos` router apply authentication at the router level, so
future endpoints added to either router inherit protection automatically.

API keys are not stored in source control. The backend reads `API_KEY` from the
environment or the ignored `backend/.env` file.

## Chat Flow

```text
POST /chat
  -> Validate Bearer API key
  -> Validate model and message
  -> POST OLLAMA_BASE_URL/api/generate with stream=false
  -> Read the generated response
  -> Return {"answer": "..."}
```

The service translates connection failures, timeouts, upstream HTTP errors,
and malformed Ollama responses into clear API errors.

## Repository Indexing Flow

```text
POST /repos/index-local
  -> Validate Bearer API key
  -> Resolve and validate the local directory
  -> Recursively discover supported files
  -> Prune ignored directories
  -> Read files as UTF-8 text
  -> Split content into line-aware chunks
  -> Atomically write data/indexes/<repo-name>.json
  -> Return file and chunk counts
```

Each chunk stores a stable file-relative identifier, relative source path,
start line, end line, and content. The index also records its source path,
creation time, supported extensions, and any files skipped because they could
not be read.

The API is intended for a trusted self-hosted environment because an
authenticated caller can ask the backend to read local directories available
to its operating-system user.

## Repository Question Flow

```text
POST /repos/ask
  -> Validate Bearer API key
  -> Load data/indexes/<repo-name>.json
  -> Normalize question terms
  -> Score chunks by content and file-path keyword overlap
  -> Select the top RAG_TOP_K chunks
  -> Build a prompt with source paths and line ranges
  -> Generate an answer with RAG_MODEL through Ollama
  -> Return the answer and unique source file paths
```

File-path matches receive a small ranking bonus. Common question words are
removed, and snake_case and camelCase identifiers are split into searchable
terms. Chunks with no overlap are not included.

The prompt tells the model to use only retrieved context, treat indexed code
as untrusted data rather than instructions, and acknowledge when the available
context is insufficient.
