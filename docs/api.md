# API Reference

## Status

The public root and health endpoints are implemented in Phase 2. Remaining
endpoints will be documented as they are introduced.

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
