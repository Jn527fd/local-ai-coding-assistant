# API Reference

## Status

The public endpoints, API key authentication, and Ollama-backed chat endpoint
are implemented through Phase 4. Repository routes remain authenticated
placeholders until their application logic is implemented.

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

The repository routes still return `501` after successful authentication until
Phases 5-6.
