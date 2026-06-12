# Architecture

## Status

Phase 4 implements the FastAPI application boundary, environment-backed
configuration, Bearer API key authentication, and local Ollama text
generation.

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
- **Repository index:** Code files split into chunks and stored as JSON under
  `data/indexes/`.
- **RAG flow:** Retrieve relevant code chunks, add them to a prompt, and send
  the prompt to Ollama.

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
