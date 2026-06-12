# Architecture

## Status

Phase 2 implements the FastAPI application boundary, environment-backed
configuration, CORS middleware, and public application health endpoints.

## Planned Components

- **Frontend:** React and Vite interface for health status, chat, repository
  indexing, and repository questions.
- **Backend:** FastAPI application that exposes health, chat, and repository
  endpoints. The application factory in `backend/app/main.py` owns startup,
  middleware, and router registration.
- **Configuration:** `backend/app/config.py` reads environment variables and an
  optional backend `.env` file using Pydantic Settings.
- **Authentication:** Bearer API key validation for AI and repository routes.
- **LLM provider:** Ollama running locally on the host machine.
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
Request -> CORS middleware -> FastAPI router -> Pydantic response validation
```

The `/` and `/health` endpoints are intentionally public. Protected endpoint
authentication will be introduced in Phase 3.
