# API Reference

## Status

The public endpoints, API key authentication, Ollama-backed chat, local
repository indexing, and keyword-based repository RAG are implemented through
Phase 6.

## Planned Endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | No | Return basic application information |
| `GET` | `/health` | No | Report backend process health |
| `POST` | `/chat` | Bearer API key | Send a message to Ollama |
| `POST` | `/repos/index-local` | Bearer API key | Index a local repository |
| `POST` | `/repos/ask` | Bearer API key | Ask a question about an index |

## `GET /`

Returns application metadata.

```json
{
  "name": "Local AI Coding Assistant",
  "version": "0.1.0",
  "environment": "development",
  "docs_url": "/docs"
}
```

## `GET /health`

Returns HTTP `200` while the backend process is accepting requests.

```json
{
  "status": "ok"
}
```

## Example Requests

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

## Authentication

Protected endpoints require this HTTP header:

```text
Authorization: Bearer YOUR_API_KEY
```

The value must match the backend `API_KEY` environment variable. Missing or
invalid credentials return:

```json
{
  "detail": "Missing or invalid API key."
}
```

with HTTP status `401` and the `WWW-Authenticate: Bearer` response header.

If the server operator did not configure `API_KEY`, protected routes return
HTTP `503` with a configuration error.

## `POST /chat`

Sends a prompt to the configured local Ollama server.

Request:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:4b","message":"Explain this function."}'
```

Successful response:

```json
{
  "answer": "The generated response from Ollama."
}
```

Possible errors:

| Status | Meaning |
| --- | --- |
| `401` | API key is missing or invalid |
| `422` | Request body is invalid |
| `502` | Ollama returned an error or malformed response |
| `503` | The backend could not connect to Ollama |
| `504` | Ollama exceeded the configured timeout |

## `POST /repos/index-local`

Recursively indexes supported files from a local directory. The path is
resolved on the backend machine and should normally be absolute.

Request:

```bash
SAMPLE_REPO_PATH="$(realpath sample-code-repository)"

curl -X POST http://localhost:8000/repos/index-local \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"$SAMPLE_REPO_PATH\"}"
```

Successful response:

```json
{
  "repo_name": "sample-code-repository",
  "indexed_files": 9,
  "indexed_chunks": 9
}
```

The generated file is stored at:

```text
data/indexes/sample-code-repository.json
```

Supported extensions are `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.md`, `.json`,
`.yaml`, `.yml`, `.html`, and `.css`.

Directories named `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, or
`build` are ignored at every depth.

Possible errors:

| Status | Meaning |
| --- | --- |
| `400` | The path does not exist, cannot be resolved, or is not a directory |
| `401` | API key is missing or invalid |
| `403` | The backend process cannot traverse the repository directory |
| `422` | Request body is invalid |
| `500` | The index file could not be written |

## `POST /repos/ask`

Retrieves relevant chunks from a previously generated JSON index, sends a
grounded prompt to Ollama, and returns the answer with source file paths.

Request:

```bash
curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "sample-code-repository",
    "question": "Where are the add and multiply functions implemented?"
  }'
```

Successful response:

```json
{
  "answer": "The functions are implemented in sample_app/calculator.py.",
  "sources": [
    "app.py",
    "sample_app/calculator.py"
  ]
}
```

The exact answer and source ordering depend on the question and local model.
Sources are unique relative paths from the ranked chunks.

Possible errors:

| Status | Meaning |
| --- | --- |
| `401` | API key is missing or invalid |
| `404` | No JSON index exists for the requested repository |
| `422` | Request body is invalid |
| `500` | The repository index is unreadable or malformed |
| `502` | Ollama returned an error or malformed response |
| `503` | The backend could not connect to Ollama |
| `504` | Ollama exceeded the configured timeout |
