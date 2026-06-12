# Local AI Coding Assistant

A self-hosted coding assistant that will chat with a local large language model,
index source repositories, and answer questions about an indexed codebase.

The project is designed for a Linux Mint laptop with an NVIDIA GPU, Docker, and
Ollama. It will use FastAPI for the backend, React with Vite for the frontend,
and a small local model such as `qwen3:4b`. No cloud LLM APIs are required.

## Project Status

Phase 6 is complete. The project includes a configurable FastAPI application,
Bearer API key authentication, local Ollama chat, JSON repository indexing,
keyword retrieval, and RAG-based repository questions.

The React frontend, Docker support, and expanded automated tests will be added
incrementally in later phases.

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

## Run the Backend

Python 3.10 or newer is recommended.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Replace API_KEY in .env with a private random value.
# OLLAMA_BASE_URL defaults to http://localhost:11434.
python -m uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`, and interactive API
documentation is available at `http://localhost:8000/docs`.

Check the endpoints:

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:4b","message":"Hello"}'
```

The `/chat` endpoint sends the message to Ollama and returns its generated
answer. `/repos/index-local` creates a JSON code index, and `/repos/ask`
retrieves relevant chunks before sending a grounded prompt to Ollama. Missing
or invalid API keys return `401 Unauthorized`.

## Prepare Ollama

Confirm Ollama is installed and pull the default model:

```bash
ollama --version
ollama pull qwen3:4b
ollama list
```

Ollama normally runs as a Linux service. If it is not running, start it in a
separate terminal:

```bash
ollama serve
```

## Index a Local Repository

The path must exist on the same machine where the FastAPI backend runs. Use an
absolute path. A ready-to-index fixture is included at
`sample-code-repository/`.

From the project root:

```bash
SAMPLE_REPO_PATH="$(realpath sample-code-repository)"

curl -X POST http://localhost:8000/repos/index-local \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"$SAMPLE_REPO_PATH\"}"
```

The backend recursively indexes supported code and documentation files,
ignores generated dependency directories, splits text into line-aware chunks,
and writes the result under `data/indexes/`.

For the included fixture, inspect:

```bash
python -m json.tool data/indexes/sample-code-repository.json | less
```

Supported extensions:

```text
.py .js .jsx .ts .tsx .md .json .yaml .yml .html .css
```

Ignored directories:

```text
.git node_modules .venv __pycache__ dist build
```

## Ask About an Indexed Repository

After indexing `sample-code-repository`, ask a question:

```bash
curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "sample-code-repository",
    "question": "Where are the add and multiply functions implemented?"
  }'
```

The response contains the Ollama answer and the relative paths of retrieved
source files:

```json
{
  "answer": "The functions are implemented in sample_app/calculator.py.",
  "sources": ["app.py", "sample_app/calculator.py"]
}
```

Retrieval currently uses transparent keyword overlap rather than embeddings.
`RAG_TOP_K` controls how many chunks are sent to Ollama, and `RAG_MODEL`
selects the local model.

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
