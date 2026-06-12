# API Reference

## Status

This document is a Phase 1 placeholder. Request and response examples will be
added as each endpoint is implemented.

## Planned Endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | No | Return basic application information |
| `GET` | `/health` | No | Report backend health |
| `POST` | `/chat` | Bearer API key | Send a message to Ollama |
| `POST` | `/repos/index-local` | Bearer API key | Index a local repository |
| `POST` | `/repos/ask` | Bearer API key | Ask a question about an index |

The final reference will document headers, schemas, status codes, errors, and
example `curl` commands.
