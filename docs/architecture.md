# Architecture

## Status

This document is a Phase 1 placeholder. It will be completed as the application
components are implemented.

## Planned Components

- **Frontend:** React and Vite interface for health status, chat, repository
  indexing, and repository questions.
- **Backend:** FastAPI application that exposes health, chat, and repository
  endpoints.
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
