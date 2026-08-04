# Frontend/Backend Compatibility Contract

This document records the compatibility decisions for the production frontend
and backend API.

## Decision

Keep backend response shapes stable and preserve the existing public API. Add
small request-body aliases where they reduce frontend adapter complexity without
breaking existing clients.

## Added Aliases

| Endpoint | Existing request | Frontend-compatible request | Response shape |
| --- | --- | --- | --- |
| `PUT /account/api-key` | `api_key` | `apiKey` | Existing snake_case fields |
| `POST /repos/ask` | `repo_name` | `repoName` | Existing repository response fields |

## Kept Frontend-Side

- Response normalization from snake_case backend fields to frontend domain
  models remains in the HTTP service layer.
- Conversation metadata compatibility remains in the conversation mapper because
  it protects both older backend records and current frontend state.
- Repository index/search response mapping remains frontend-side until an
  explicit API versioning phase decides whether response aliases are worth the
  migration cost.

## Compatibility Requirements

- Existing clients using `api_key` and `repo_name` must continue to work.
- Frontend clients may send `apiKey` and `repoName`.
- Backend default tests remain hermetic and must not require Ollama.
- No alias may expose secrets or change redaction behavior.

## Deferred

- Versioned API routes such as `/v2/...`.
- Dual snake_case/camelCase response payloads.
- Moving all frontend adapter mapping into backend serializers.
