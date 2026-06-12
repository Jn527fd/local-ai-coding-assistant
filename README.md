# Local AI Coding Assistant

A self-hosted coding assistant that will chat with a local large language model,
index source repositories, and answer questions about an indexed codebase.

The project is designed for a Linux Mint laptop with an NVIDIA GPU, Docker, and
Ollama. It will use FastAPI for the backend, React with Vite for the frontend,
and a small local model such as `qwen3:4b`. No cloud LLM APIs are required.

## Project Status

Phase 1 is complete: the project structure and initial documentation have been
created. Application code will be added incrementally in later phases.

## Planned Features

- FastAPI backend with health checks and environment-based configuration
- Bearer API key authentication for protected endpoints
- Local Ollama chat integration
- Local and GitHub repository indexing
- Simple JSON-based code chunk index
- Keyword retrieval and retrieval-augmented generation (RAG)
- React and Vite user interface
- Docker Compose development environment
- Automated backend tests

## Planned Architecture

```text
React frontend
      |
      | HTTP + Bearer API key
      v
FastAPI backend
      |--------------------|
      v                    v
Ollama local model    Repository index
                           |
                           v
                    RAG retrieval flow
```

## Repository Layout

```text
local-ai-coding-assistant/
|-- backend/
|   `-- app/
|       |-- auth/
|       |-- rag/
|       |-- routers/
|       |-- schemas/
|       |-- services/
|       `-- utils/
|-- frontend/
|   `-- src/
|       `-- components/
|-- tests/
|-- scripts/
|-- docs/
|-- data/
|   |-- indexes/
|   `-- repos/
|-- Makefile
|-- LICENSE
`-- README.md
```

## Documentation

- [Architecture](docs/architecture.md)
- [API](docs/api.md)
- [Setup](docs/setup.md)

## Development Roadmap

1. Project scaffold and documentation
2. FastAPI application and health endpoint
3. API key authentication
4. Ollama chat integration
5. Repository indexing
6. Basic RAG workflow
7. React and Vite frontend
8. Docker support
9. Automated tests
10. Complete project documentation

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for
details.
