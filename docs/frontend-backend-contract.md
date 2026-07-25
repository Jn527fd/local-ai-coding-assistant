# Frontend/Backend Compatibility Contract

This document records the Phase 22 compatibility decision for the proposed
frontend migration.

## Decision

Keep backend response shapes stable and preserve the existing public API. Add
small request-body aliases where they reduce proposed frontend adapter
complexity without breaking legacy clients.

## Added Aliases

| Endpoint | Legacy request | Proposed-compatible request | Response shape |
| --- | --- | --- | --- |
| `PUT /account/api-key` | `api_key` | `apiKey` | Existing snake_case fields |
| `POST /repos/ask` | `repo_name` | `repoName` | Existing repository response fields |

## Kept Frontend-Side

- Response normalization from snake_case backend fields to proposed frontend
  domain models remains in the proposed HTTP service layer.
- Conversation metadata compatibility remains in the proposed conversation
  mapper because it protects both older backend records and proposed frontend
  state.
- Repository index/search response mapping remains frontend-side until an
  explicit API versioning phase decides whether response aliases are worth the
  migration cost.

## Compatibility Requirements

- Existing clients using `api_key` and `repo_name` must continue to work.
- Proposed clients may send `apiKey` and `repoName`.
- Backend default tests remain hermetic and must not require Ollama.
- No alias may expose secrets or change redaction behavior.

## Deferred

- Versioned API routes such as `/v2/...`.
- Dual snake_case/camelCase response payloads.
- Moving all proposed frontend adapter mapping into backend serializers.
