# Proposed Frontend Parity Report

This report tracks user-facing workflow parity between the current frontend in
`frontend/` and the proposed frontend in `proposedFrontend/`.

## Phase 21 Audit Summary

Phase 21 reviewed the current `frontend/src/App.jsx` workflows and the proposed
frontend routes, services, and component tests. The proposed frontend now has
coverage for the primary local-AI workflows that have been migrated so far.

## Workflow Coverage

| Workflow | Current frontend evidence | Proposed frontend coverage | Status |
| --- | --- | --- | --- |
| Authentication and local account access | Login page, stored API key, session restore | Login/signup routes, auth provider, account service, API-key storage | Covered |
| Browser-local and backend conversation persistence | Local storage fallback, migration to backend persistence | Conversation service, HTTP mapper, mock persistence, temporary chats, list/read/create/update/delete | Covered |
| Chat send and streaming | Chat composer, response streaming, stop/retry/delete | Message service, streaming SSE adapter, transcript state and retry/stop semantics | Covered |
| Per-chat model/RAG configuration | Conversation settings and model capability selection | Configuration modal, component capability service, backend settings mapper | Covered |
| Document upload, processing, and jobs | Source uploads, document processing/indexing progress | Source service, job polling, source tray workflow, document regression tests | Covered |
| RAG source metadata | Source indicators, warnings, scores | Transcript citations with vector/rerank/compression metadata | Covered |
| Repository intelligence | Keyword repo indexing and ask workflows | Repositories page, HTTP/mock repository service, vector opt-in flows | Covered |
| Diagnostics and support bundle | Diagnostics panel, status, support bundle export | Diagnostics page, HTTP/mock diagnostics service, redaction messaging | Covered |
| Profile and preferences | Account panel and browser-local preferences | Profile page, browser-local HTTP presentation preferences, mock profile editing | Covered |
| App settings | Settings section and local preferences | Settings page, local settings storage, save/reset behavior | Covered |
| Navigation | Navigation rail sections and command entry points | Protected routes plus account menu destinations | Covered |

## Small Parity Fix Applied

- The proposed account menu now navigates to `/help` for Help instead of showing
  a transient notice. This matches the protected-route surface and keeps account
  menu destinations consistent.

## Deferred Items

- The proposed Help route remains a placeholder, matching the migration plan
  rather than adding new help content in this phase.
- Password reset and email-only signup routes remain route-contract
  placeholders.
- Final backend adapter cleanup is deferred to Phase 22.

## Phase 21 Result

No current migrated user-facing capability was found to be missing from the
proposed frontend route/service surface. Phase 22 can proceed with backend
compatibility cleanup after review.
