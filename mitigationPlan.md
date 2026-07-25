# Proposed Frontend Migration Mitigation Plan

This plan covers migration from the current `frontend/` application to the
newer TypeScript frontend in `proposedFrontend/`.

The migration strategy is adapter-first: keep the proposed frontend
side-by-side, preserve the current backend behavior, replace browser mocks with
typed HTTP adapters, and promote the proposed frontend only after feature
parity and release verification are complete.

## Current Findings

- `proposedFrontend/` is a React 19, Vite 8, TypeScript, React Router, pnpm
  application with strict domain models, service interfaces, mock services,
  Vitest tests, Playwright tests, and a backend handoff OpenAPI draft.
- The proposed frontend defaults to mocks through `src/services/index.ts`.
  After Phase 4, `VITE_USE_MOCK_API=false` selects the HTTP service factory,
  which intentionally returns clear not-connected errors until real adapters
  are implemented.
- The existing backend is already feature-rich and should not be replaced:
  auth/session cookies, API-key protected chat/documents/repos, component
  discovery, conversations, jobs, diagnostics, vector stores, RAG, reranking,
  compression, OCR/PDF parsing, repo intelligence, and SSE streaming.
- The current `frontend/src/api.js` contains important backend integration
  behavior that must be ported: API base resolution, credentials, CSRF header
  forwarding, Bearer API key use, FastAPI error parsing, document/job/vector
  helpers, and backend SSE parsing.

## Key Integration Risks

- Auth mismatch: proposed frontend expects an access-token `AuthSession`; the
  backend uses HttpOnly session cookies plus CSRF for account controls and a
  separate Bearer API key for AI/data endpoints.
- Route mismatch: proposed handoff paths such as `/auth/sign-in` and
  `/conversations/{id}/messages/stream` do not exist; backend paths include
  `/auth/login`, `/auth/me`, `/chat`, and `/chat/stream`.
- Payload mismatch: proposed `modelConfiguration.embedder` maps to backend
  `conversationSettings.embedderModel`.
- Source/document mismatch: proposed `SourceService` maps to backend
  `/documents`, process/index jobs, document search, and RAG document IDs.
- Streaming mismatch: proposed events are `accepted`, `delta`, `complete`, and
  `failed`; backend events are `progress`, `metadata`, `token`, `done`, and
  `error`.
- Profile mismatch: proposed profile UI expects richer profile APIs than the
  backend currently exposes.
- Cutover risk: replacing `frontend/` before parity would risk losing
  diagnostics, repo tools, API-key setup, document jobs, and RAG metadata.

## Phase 1: Migration Baseline and Contract Inventory

### Objective

Freeze the current working state and document the exact backend/proposed
frontend contract gaps before any migration edits.

### Implementation Tasks

- Run current backend and frontend verification where available.
- Run proposed frontend verification where available.
- Compare backend routers with `proposedFrontend/docs/backend-api.openapi.yaml`.
- Create an integration gap matrix: supported, adapter-only,
  backend-change-needed, and deferred.
- Record baseline risks and recommended first integration path.

### Testing Requirements

- Current backend full pytest.
- Current frontend lint/build.
- Proposed frontend typecheck/test/build when dependencies are available.
- No code behavior changes.

### Verification Criteria

- Baseline command results are recorded honestly.
- API gap matrix exists.
- No backend or frontend runtime behavior is changed.
- Phase 2 has not started.

### Deliverables

- This migration plan.
- `docs/proposed-frontend-migration.md`.
- Baseline command results in the final report.

## Phase 2: Keep Proposed Frontend Side-by-Side

Objective: Make `proposedFrontend` runnable and testable without disturbing the
current app.

Tasks:
- Add root commands for proposed frontend validation.
- Document current vs proposed frontend development workflows.
- Confirm dev ports do not conflict.
- Keep mocks as the default runtime.

Testing:
- Proposed frontend build/test/typecheck.
- Current frontend and backend regression checks.

Deliverables:
- Side-by-side workflow docs.
- Proposed frontend Makefile or script commands.

### Phase 2 Completion Notes

- Added root commands for installing, running, and validating the proposed
  frontend without replacing `frontend/`.
- Documented the current frontend on port `5173` and the proposed frontend on
  port `8443`.
- Confirmed the proposed frontend remains mock-backed by default.
- Deferred real backend adapter work to later phases.

### Phase 2 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `make help` | Blocked | `make` is not installed or not on `PATH` in this PowerShell shell. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py` | Passed | Backend smoke passed: 9 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `pnpm validate` from `proposedFrontend/` | Blocked | Proposed frontend dependencies are incomplete. pnpm attempted install, but registry access failed with `EACCES` and `fetch failed`. |

### Phase 2 Conclusion

Phase 2 is complete with an environment limitation: this shell cannot execute
`make`, and the proposed frontend cannot validate until dependencies are
installed on a machine with registry access. The current backend and current
frontend remain healthy. It is safe to proceed to Phase 3 after approval
because Phase 2 only added side-by-side commands and documentation.

## Phase 3: API Client Hardening

Objective: Port practical backend integration behavior into the proposed API
client.

Tasks:
- Add `credentials: "include"` support.
- Read CSRF cookie and send `X-CSRF-Token` on unsafe requests.
- Preserve `X-Request-ID`.
- Parse FastAPI `detail` errors.
- Support multipart form data.

Testing:
- API client unit tests for JSON, no-content, multipart, CSRF, and errors.

Deliverables:
- Hardened `proposedFrontend/src/api/client.ts`.

### Phase 3 Completion Notes

- Hardened `proposedFrontend/src/api/client.ts` with backend-compatible
  request behavior.
- Added cookie credentials by default so existing session-cookie auth can work.
- Added CSRF cookie forwarding for unsafe methods using `local_ai_csrf`.
- Added multipart `FormData` support without forcing a JSON content type.
- Added no-content response handling.
- Added FastAPI `detail` error parsing for string and validation-array errors.
- Preserved Bearer token support and request ID behavior.
- Added focused API client tests for JSON, 204 responses, CSRF, multipart,
  backend error envelopes, and FastAPI error shapes.
- Did not add service selection or HTTP adapters; those remain Phase 4.

### Phase 3 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `pnpm exec vitest run src/api/client.test.ts` from `proposedFrontend/` | Blocked | Proposed frontend dependencies are incomplete. pnpm attempted install, but registry access failed with `EACCES` and `fetch failed` before Vitest started. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py` | Passed | Backend smoke passed: 9 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | No whitespace errors; Windows reported expected LF-to-CRLF warnings on existing edited files. |

### Phase 3 Conclusion

Phase 3 is complete with the same proposed-frontend dependency limitation from
Phase 1 and Phase 2. The current backend and current frontend remain healthy.
It is safe to proceed to Phase 4 after approval, provided Phase 4 starts by
installing or validating proposed frontend dependencies in an environment with
registry access.

## Phase 4: Runtime Service Selection

Objective: Switch between mock services and HTTP services by environment.

Tasks:
- Implement `VITE_USE_MOCK_API` selection.
- Add `src/services/http/createHttpServices.ts`.
- Keep mocks available for tests and offline design work.

Testing:
- Mock mode tests remain green.
- HTTP factory tests with fake fetch.

Deliverables:
- Runtime service adapter boundary.

### Phase 4 Completion Notes

- `VITE_USE_MOCK_API` now controls proposed frontend service selection.
- Mock services remain the default.
- `VITE_USE_MOCK_API=false` selects a new HTTP service factory.
- The HTTP factory currently returns explicit `501` not-connected `AppError`s
  for all service methods.
- Added focused service-selection tests.
- No backend route mappings, auth adapter, or real HTTP adapter behavior were
  implemented.

### Phase 4 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/index.test.ts src/api/client.test.ts` from `proposedFrontend/` | Passed | Focused proposed frontend suite passed: 2 files, 11 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py` | Passed | Backend smoke passed: 9 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | No whitespace errors; Windows reported expected LF-to-CRLF warnings on existing edited files. |

### Phase 4 Conclusion

Phase 4 is implemented and the focused proposed frontend tests now pass after
exporting `createApiClient` from the API barrel. The current backend and
current frontend remain healthy. It is safe to proceed to Phase 5 after
approval.

## Phase 5: Auth Adapter Compatibility

Objective: Connect proposed login/logout/session restore to existing backend
auth.

Tasks:
- Map sign-in to `/auth/login`.
- Map restore session to `/auth/me`.
- Map sign-out to `/auth/logout`.
- Derive proposed `AuthSession` from backend username response.
- Defer signup/OAuth or keep mock-only with clear disabled states.

Testing:
- Auth adapter tests.
- Login/logout UI tests.
- Backend auth regression tests.

Deliverables:
- Real login flow in proposed frontend.

### Phase 5 Completion Notes

- Implemented the proposed frontend HTTP auth adapter for existing backend
  routes:
  - `signIn` maps to `POST /auth/login`.
  - `restoreSession` maps to `GET /auth/me`.
  - `signOut` maps to `POST /auth/logout`.
- Backend username sessions are mapped into the proposed `AuthSession` shape
  with cookie-backed empty `accessToken` values.
- Unauthorized session restore now resolves to `null`, matching the proposed
  `AuthService.restoreSession` contract.
- Signup, email verification, account creation, and OAuth remain explicit
  not-connected operations.
- API-key/account bridging is not implemented; that remains Phase 6.

### Phase 5 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/index.test.ts src/api/client.test.ts` from `proposedFrontend/` | Passed | Proposed focused suite passed: 3 files, 16 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py` | Passed | Backend smoke/auth suite passed: 16 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |

### Phase 5 Conclusion

Phase 5 is complete. It is safe to proceed to Phase 6 after approval. Phase 6
should add the API-key/account bridge needed for chat, documents,
repositories, diagnostics, and vector endpoints.

## Phase 6: API Key and Account Bridge

Objective: Preserve the existing API-key workflow required by AI/data routes.

Tasks:
- Connect `/account/status`.
- Connect `/account/api-key`.
- Store API key using an explicit frontend boundary.
- Ensure chat, documents, repos, diagnostics, and vector endpoints can send the
  Bearer key.

Testing:
- API-key save/status tests.
- Unauthorized route tests.

Deliverables:
- Real API-key setup in proposed UI.

### Phase 6 Completion Notes

- Added an `AccountService` contract to the proposed frontend service layer.
- Added a browser API-key storage boundary using the current app's compatible
  `local-ai-coding-assistant.api-key` localStorage key.
- Implemented mock account status and API-key update behavior.
- Implemented HTTP account status and API-key update mappings:
  - `getStatus` maps to `GET /account/status`.
  - `updateApiKey` maps to `PUT /account/api-key`.
- `getStatus` sends the stored or supplied API key as `Authorization: Bearer`.
- `updateApiKey` persists the key locally after the backend accepts it.
- No chat, document, repository, diagnostics, or vector adapters were added.

### Phase 6 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/apiKeyStorage.test.ts src/services/mock/createMockServices.test.ts src/services/index.test.ts` from `proposedFrontend/` | Passed | Proposed focused suite passed: 4 files, 25 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py` | Passed | Backend smoke/auth/account suite passed: 18 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |

### Phase 6 Conclusion

Phase 6 is complete. It is safe to proceed to Phase 7 after approval. Phase 7
should replace proposed frontend static model/tool options with real
`/components/capabilities` data.

## Phase 7: Real Component Capabilities

Objective: Replace hardcoded model/tool lists with backend discovery.

Tasks:
- Connect `/components/capabilities`.
- Map capability categories into configuration options.
- Map `embedder` to backend `embedderModel`.
- Set defaults from available backend capabilities.

Testing:
- Capability adapter tests.
- Empty/unavailable-state tests.
- Configuration modal tests.

Deliverables:
- Real per-chat model/tool settings.

### Phase 7 Completion Notes

Phase 7 is complete.

Implemented:
- Added proposed frontend capability domain types and a capability service
  contract.
- Connected HTTP mode to `GET /components/capabilities`.
- Added mock capability fixtures so mock mode remains offline and deterministic.
- Replaced static chat configuration model/tool options with discovered
  capability options.
- Added capability-derived defaults for new conversations once discovery
  returns available backend capabilities.
- Kept detected-but-unavailable tools visible and disabled in the configuration
  modal.

Verification:
- Proposed focused capability/service/modal tests passed.
- Proposed frontend TypeScript check passed.
- Backend component/auth/account smoke tests passed.
- Current frontend lint and production build passed.

Phase 7 is safe to proceed from. Phase 8 should begin only after approval.

## Phase 8: Conversation List Adapter

Objective: Load backend-persisted conversations into the proposed sidebar.

Tasks:
- Map `/conversations` list/get/create/delete.
- Preserve temporary conversation UX locally until backend semantics are agreed.
- Handle deleting active or last conversation.

Testing:
- Conversation list/get/delete tests.
- Sidebar workflow tests.

Deliverables:
- Real conversation history in proposed frontend.

### Phase 8 Completion Notes

Phase 8 is complete.

Implemented:
- Connected proposed frontend HTTP conversation list/get/create/delete methods
  to the backend `/conversations` API.
- Added a conservative backend conversation mapper that preserves proposed-created
  metadata while applying safe defaults to older backend records.
- Added local-only handling for temporary conversations in HTTP mode, so
  temporary chats are not persisted until backend semantics are agreed.
- Made initial app state loading tolerate the still-unconnected HTTP source
  service, allowing persisted conversations to load independently.
- Added focused HTTP conversation adapter tests and a sidebar action regression
  test.

Deferred:
- Full message/settings/source shape migration remains Phase 9.
- Rename and configuration save persistence remains Phase 10.
- Source/document service adapters remain later phases.

Phase 8 is safe to proceed from. Phase 9 should begin only after approval.

## Phase 9: Conversation Shape Migration

Objective: Map backend stored records into the proposed conversation domain.

Tasks:
- Convert backend messages/settings/metadata into proposed `Conversation`.
- Add defaults for missing fields.
- Preserve source IDs, system prompt, model config, and temporary flag.

Testing:
- DTO mapping fixture tests.
- Reload/deep-link tests.

Deliverables:
- Stable conversation mapper.

### Phase 9 Completion Notes

Phase 9 is complete.

Implemented:
- Extracted backend/proposed conversation shape conversion into a dedicated
  proposed frontend HTTP conversation mapper.
- Added stable mapping for backend messages, message status, attachments,
  conversation settings, system prompt, source IDs, and temporary flags.
- Preserved backend `chunker` and `ragPipeline` settings in the proposed
  `ModelConfiguration` type even before their UI controls are exposed.
- Added safe fallback behavior for older or partial backend records.
- Kept proposed-only fields round-tripped under `metadata.proposedFrontend`.
- Added direct mapper fixture tests and retained Phase 8 HTTP/sidebar coverage.

Deferred:
- Rename and configuration save persistence remains Phase 10.
- Chat send/stream adapters remain later phases.

Phase 9 is safe to proceed from. Phase 10 should begin only after approval.

## Phase 10: Rename and Configuration Saves

Objective: Persist proposed conversation edits.

Tasks:
- Map rename to backend upsert/update behavior.
- Map configuration changes to backend conversation records.
- Preserve per-chat settings isolation.

Testing:
- Rename tests.
- Per-chat config isolation tests.

Deliverables:
- Persistent titles, prompts, and settings.

### Phase 10 Completion Notes

Phase 10 is complete.

Implemented:
- Connected proposed frontend HTTP conversation rename to backend
  `PUT /conversations/{id}` using get-merge-update semantics.
- Connected proposed frontend HTTP configuration saves to backend
  `PUT /conversations/{id}`.
- Preserved existing backend metadata while updating proposed-only metadata under
  `metadata.proposedFrontend`.
- Preserved per-chat settings isolation by fetching and updating only the target
  conversation.
- Kept temporary conversation rename/configuration changes local-only.

Deferred:
- Basic chat message send remains Phase 11.
- Streaming remains Phase 12.

Phase 10 is safe to proceed from. Phase 11 should begin only after approval.

## Phase 11: Basic Non-Streaming Chat Adapter

Objective: Get real chat working before streaming.

Tasks:
- Map `MessageService.send` to `/chat`.
- Build backend `ChatRequest` from proposed conversation state.
- Convert `ChatResponse` to an assistant `ChatMessage`.

Testing:
- Message adapter tests.
- No-RAG chat integration test with fake backend.

Deliverables:
- Real non-streaming chat in proposed frontend.

### Phase 11 Completion Notes

Phase 11 is complete.

Implemented:
- Connected proposed frontend HTTP `MessageService.send` to backend
  `POST /chat`.
- Built backend `ChatRequest` payloads from the active proposed conversation,
  including history, conversation settings, and attachment document IDs.
- Forwarded the stored API key as a bearer token when configured.
- Converted backend `ChatResponse.answer` into a proposed assistant
  `ChatMessage`.
- Added a temporary non-SSE `MessageService.stream` wrapper that emits accepted
  and complete events from the one-shot `/chat` response so the current UI can
  exercise real chat before Phase 12 streaming.
- Kept transcript updates in memory only; durable message persistence remains
  Phase 13.

Deferred:
- Real SSE `/chat/stream` parsing remains Phase 12.
- Durable transcript persistence remains Phase 13.

Phase 11 is safe to proceed from. Phase 12 should begin only after approval.

## Phase 12: Backend Stream Adapter

Objective: Adapt backend SSE to proposed streaming UI.

Tasks:
- Map `/chat/stream` events from `progress`, `metadata`, `token`, `done`,
  `error` into proposed stream events.
- Preserve message IDs where available and generate local pending IDs where
  necessary.
- Normalize disconnects into retryable errors.

Testing:
- SSE parser tests.
- Token accumulation and failure tests.

Deliverables:
- Real streaming chat.

### Phase 12 Completion Notes

Phase 12 is complete.

Implemented:
- Replaced the temporary one-shot stream wrapper with a real
  `POST /chat/stream` SSE adapter.
- Parsed backend `progress`, `metadata`, `token`, `done`, and `error` events.
- Mapped backend `token` events to proposed `delta` events.
- Mapped backend `done` events to proposed completed assistant messages.
- Mapped backend `error` events and premature disconnects to proposed failed
  assistant messages.
- Preserved generated local user/assistant message IDs for the accepted,
  delta, complete, and failed event sequence.
- Forwarded stored API keys and CSRF headers for stream requests.

Deferred:
- Durable transcript persistence remains Phase 13.
- Retry/cancel backend adapters remain future phases.

Phase 12 is safe to proceed from. Phase 13 should begin only after approval.

## Phase 13: Message Persistence Strategy

Objective: Ensure messages survive reloads without duplication.

Tasks:
- Decide whether frontend saves messages through conversations after chat or
  backend chat persists them.
- Start with the smallest adapter-level persistence path.
- Handle failed/stopped/retry states.

Testing:
- Send/reload/restore tests.
- Duplicate prevention tests.

Deliverables:
- Durable transcripts in proposed frontend.

### Phase 13 Completion Notes

Phase 13 is complete.

- Decided to persist proposed frontend chat transcripts at the adapter layer by
  writing the updated conversation record through the existing
  `PUT /conversations/{id}` endpoint after chat completion or failure.
- Kept temporary conversations local-only.
- Preserved the local transcript if the backend persistence write fails after a
  successful generation.
- Added regression coverage for non-streaming persistence, streaming
  persistence, and persistence failure fallback.
- Did not add new backend endpoints or schema changes.

Phase 13 is safe to proceed from. Phase 14 should begin only after approval.

## Phase 14: Source-to-Document Adapter

Objective: Connect proposed `SourceService` to backend document APIs.

Tasks:
- Map source list/upload/delete to document APIs.
- Represent upload, processing, indexing, ready, and failed states.
- Add backend delete only if required and small.

Testing:
- Upload/list/error tests.
- Backend document regression tests.

Deliverables:
- Real source/document list and uploads.

### Phase 14 Completion Notes

Phase 14 is complete.

- Connected proposed frontend HTTP `SourceService.list` to backend
  `GET /documents?conversationId=...`.
- Connected `SourceService.upload` to backend `POST /documents/upload` with
  `conversationId`, file form data, and active conversation settings.
- Added chunk-preview summaries through `GET /documents/{id}/chunks`.
- Mapped backend document statuses into proposed source statuses:
  `indexed` -> `ready`, `uploaded`/`processed` -> `processing`,
  `failed` -> `failed`.
- Tightened the proposed source upload picker and validation to backend
  supported document types: PDF, DOCX, TXT, Markdown, HTML, CSV, and TSV.
- Kept delete and retry deferred because the backend has no document delete or
  retry endpoint yet; job-backed processing/indexing remains Phase 15.

Phase 14 is safe to proceed from. Phase 15 should begin only after approval.

## Phase 15: Document Processing and Indexing Jobs

Objective: Wire source status to backend job progress.

Tasks:
- Start process/index jobs after upload where needed.
- Poll `/jobs/{id}`.
- Surface progress and failure states.

Testing:
- Job polling tests.
- Progress UI tests.

Deliverables:
- End-to-end document ingestion.

### Phase 15 Completion Notes

Phase 15 is complete.

- Proposed frontend HTTP source uploads now stage the file, start a backend
  process job, poll `/jobs/{id}`, start an index job, and poll that job before
  returning the final source state.
- Successful process/index orchestration returns uploaded sources as `ready`.
- Process or index job failures return the affected source as `failed` with the
  backend job error/message.
- `SourceService.retry` now re-runs process and index jobs for an existing
  document.
- The existing modal upload progress indicator continues to cover the
  upload/process/index wait; richer per-job progress UI is still available for
  a later polish phase.

Phase 15 is safe to proceed from. Phase 16 should begin only after approval.

## Phase 16: RAG Source Selection

Objective: Make selected sources affect chat retrieval.

Tasks:
- Map selected source IDs to `ragOptions.documentIds`.
- Include `attachmentDocumentIds` when appropriate.
- Remove deleted source IDs from conversations.

Testing:
- Selected-source request tests.
- RAG metadata regression tests.

Deliverables:
- Chat against selected documents.

### Phase 16 Completion Notes

Phase 16 is complete.

- Proposed frontend HTTP chat requests now send selected conversation
  `sourceIds` as `ragOptions.documentIds`.
- Ready composer document attachments remain in `attachmentDocumentIds` and are
  also included in RAG document IDs.
- Selected and attached document IDs are deduplicated before sending.
- Plain chat requests with no selected or attached sources do not enable
  `ragOptions`, preserving existing non-RAG behavior.
- Existing source delete UI already removes deleted IDs from local conversation
  state when deletion succeeds; backend document delete remains unavailable.

Phase 16 is safe to proceed from. Phase 17 should begin only after approval.

## Phase 17: Source Citations and Metadata UI

Objective: Display backend RAG, rerank, compression, and source metadata.

Tasks:
- Extend proposed message/source metadata types if needed.
- Render source number, document, page, vector score, rerank score, final rank,
  and warnings.

Testing:
- Citation rendering tests.
- Accessibility checks.

Deliverables:
- Reliable RAG source visibility.

### Phase 17 Completion Notes

Phase 17 is complete.

- Added optional chat message metadata for backend RAG, rerank, compression,
  warnings, and source citations.
- HTTP chat adapters now attach metadata from both `/chat` responses and
  `/chat/stream` metadata/done events.
- Conversation mapping now preserves message metadata through backend
  persistence and reloads.
- Chat transcript now renders compact source citation cards with source number,
  document name, page, final rank, vector score, rerank score, and preview text.
- RAG, rerank, and compression warnings are shown alongside assistant messages.
- Plain messages without metadata render unchanged.

Phase 17 is safe to proceed from. Phase 18 should begin only after approval.

## Phase 18: Profile and Account Reality Check

Objective: Reconcile proposed profile UX with backend account capabilities.

Tasks:
- Classify profile fields as real, local-only, or deferred.
- Connect available account/API-key data.
- Disable unsupported avatar/profile deletion/export controls or add small
  backend support if justified.

Testing:
- Profile/account state tests.

Deliverables:
- Honest profile/settings UX.

### Phase 18 Completion Notes

Phase 18 is complete.

- Classified HTTP profile behavior as backend-backed account status plus
  browser-local presentation preferences.
- Added profile service capability metadata so unsupported avatar upload can be
  disabled instead of pretending to be connected.
- HTTP profile loading now uses `/auth/me` and `/account/status`.
- HTTP profile edits are stored as browser-local preferences.
- HTTP profile export now includes local profile data plus support metadata that
  identifies profile preferences as browser-local and avatar upload as
  unsupported.
- Mock profile behavior remains richer for prototype/demo mode.

Phase 18 is safe to proceed from. Phase 19 should begin only after approval.

## Phase 19: Repository Intelligence UI Integration

Objective: Preserve current repository features.

Tasks:
- Add or adapt proposed UI for `/repos/index-local`, `/repos/index-local/vector`,
  `/repos/ask`, and `/repos/search-vector`.
- Surface path validation and stale-index warnings.

Testing:
- Repo workflow tests.

Deliverables:
- Repo intelligence parity.

### Phase 19 Completion Notes

Phase 19 is complete.

- Added a proposed frontend repository service boundary for keyword indexing,
  keyword repository Q&A, opt-in vector indexing, and vector search.
- Connected HTTP mode to `/repos/index-local`, `/repos/index-local/vector`,
  `/repos/ask`, and `/repos/search-vector`.
- Added mock repository behavior so the proposed frontend remains usable in
  default mock mode.
- Added a protected Repositories page reachable from the account menu.
- The page surfaces path validation errors, backend request errors, stale-index
  warnings, keyword-RAG sources, and vector search metadata.
- Existing backend repository APIs and legacy keyword RAG behavior are
  preserved.

Phase 19 is safe to proceed from. Phase 20 should begin only after approval.

## Phase 20: Diagnostics Panel Migration

Objective: Bring diagnostics and support bundles into the proposed frontend.

Tasks:
- Connect `/diagnostics/status`.
- Connect `/diagnostics/support-bundle`.
- Preserve redaction messaging.

Testing:
- Diagnostics panel tests.

Deliverables:
- Diagnostics parity.

### Phase 20 Completion Notes

- Added a proposed-frontend diagnostics service boundary in mock and HTTP modes.
- HTTP mode calls `/diagnostics/status` and `/diagnostics/support-bundle`.
- Mock mode returns deterministic diagnostics and a redacted support bundle.
- Added a protected `/diagnostics` page reachable from the account menu.
- The diagnostics page preserves redaction messaging and exports support bundle
  JSON without displaying sensitive raw content inline.
- Phase 20 verification passed; it is safe to proceed to Phase 21 after review.

## Phase 21: Navigation and Feature Parity Audit

Objective: Confirm no current user-facing capability was lost.

Tasks:
- Compare against current `frontend/src/App.jsx` workflows.
- Audit chat, account, settings, documents, jobs, repos, diagnostics, and
  conversations.
- Fix small parity gaps.

Testing:
- Manual smoke checklist.
- Component workflow tests.

Deliverables:
- Feature parity report.

### Phase 21 Completion Notes

- Added `docs/proposed-frontend-parity-report.md` with audited workflow parity
  across chat, account, settings, documents, jobs, repositories, diagnostics,
  conversations, navigation, and profile workflows.
- Fixed a small account-menu parity gap so Help navigates to `/help` like the
  other protected menu destinations.
- Added component workflow coverage for account-menu navigation destinations
  and logout handling.
- Phase 21 verification passed; it is safe to proceed to Phase 22 after review.

## Phase 22: Backend Compatibility Cleanup

Objective: Decide whether adapter mappings should remain frontend-only or move
to backend aliases.

Tasks:
- Review adapter complexity.
- Add backend alias endpoints only if they reduce long-term maintenance.
- Preserve current backend API compatibility.

Testing:
- Backend route compatibility tests.

Deliverables:
- Stable frontend/backend contract.

### Phase 22 Completion Notes

- Added backend request aliases for the two remaining high-value proposed
  frontend compatibility gaps:
  - `PUT /account/api-key` accepts `apiKey` as well as `api_key`.
  - `POST /repos/ask` accepts `repoName` as well as `repo_name`.
- Kept backend response shapes stable to preserve existing API compatibility.
- Updated the proposed HTTP adapter to use the camelCase request aliases.
- Added `docs/frontend-backend-contract.md` documenting the Phase 22 contract
  decision and deferred API-versioning work.
- Phase 22 verification passed; it is safe to proceed to Phase 23 after review.

## Phase 23: Replace Current Frontend Build Target

Objective: Promote the proposed frontend as the main app.

Tasks:
- Move or point `frontend/` to the proposed app.
- Update Dockerfile, nginx, Compose, CI, and Makefile.
- Archive or remove the old frontend only after approval.

Testing:
- Frontend lint/typecheck/test/build.
- Docker frontend build.
- Backend full tests.

Deliverables:
- Proposed frontend becomes the production frontend.

### Phase 23 Completion Notes

- Promoted `proposedFrontend/` as the production frontend build target for
  Makefile commands, Docker Compose, Docker test Compose, production Compose,
  and GitHub Actions CI.
- Added `proposedFrontend/Dockerfile`, `proposedFrontend/Dockerfile.test`, and
  `proposedFrontend/nginx.conf`.
- Updated setup/start scripts to install and run the promoted frontend with
  pnpm/Corepack.
- Kept the legacy `frontend/` folder intact and available through explicit
  `legacy` Makefile targets for comparison.
- Phase 23 local frontend/backend verification passed.
- Follow-up blocker resolution created local ignored `backend/.env` from the
  safe example, validated default/prod/test Compose config, and successfully
  built the promoted frontend Docker image plus the default Compose `frontend`
  service.
- `make` is not installed in this PowerShell environment, but the underlying
  target commands were run directly and passed.
- It is safe to proceed to Phase 24 after review.

## Phase 24: End-to-End Release Verification

Objective: Prove the migrated app works end to end.

Tasks:
- Run backend full pytest.
- Run frontend unit/component/e2e tests.
- Run Docker test stack where available.
- Run optional live Ollama smoke.

Testing:
- Full local and Docker suites.

Deliverables:
- Verification log and release checklist updates.

### Phase 24 Completion Notes

- Ran the promoted frontend and backend through local and Docker verification.
- Fixed one Docker-only frontend test timeout by giving the long repository
  workflow test a 15-second budget; product behavior was unchanged.
- Replaced formatter-sensitive inline object test types with small interfaces
  in the HTTP service tests so `oxfmt`, ESLint, TypeScript, and Vitest agree.
- Local backend pytest, proposed frontend format/lint/typecheck/tests/build,
  Playwright e2e, Compose config validation, Docker image builds, Docker
  backend tests, and Docker frontend tests all passed.
- Optional live Ollama smoke tests were verified as opt-in and skipped cleanly
  without `RUN_OLLAMA_TESTS=1`.
- It is safe to proceed to Phase 25 after review.

## Phase 25: Public Release Polish

Objective: Prepare the migrated frontend for public release.

Tasks:
- Update README screenshots and feature copy.
- Update `CHANGELOG.md`.
- Update API/setup/testing/deployment docs.
- Document remaining limitations.

Testing:
- Full release checklist.
- `git diff --check`.

Deliverables:
- Release-ready migration report.

### Phase 25 Completion Notes

- Refreshed public-release copy now that `proposedFrontend/` is the production
  frontend target.
- Updated stale release checklist, changelog, backup, dependency-review, and
  README references that still treated frontend verification or promotion as
  pending.
- Added a README manual smoke path for running the promoted frontend against
  the local backend.
- Recorded final Phase 25 verification in `docs/proposed-frontend-migration.md`
  and `docs/verification-log.md`.
- The 25-phase frontend migration plan is complete.

## Phase 1 Status

Phase 1 is complete.

### Files Created

- `mitigationPlan.md`
- `docs/proposed-frontend-migration.md`

### Baseline Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Current backend suite passed: 183 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `pnpm --version` from `proposedFrontend/` | Passed | pnpm 11.9.0 is available. |
| `pnpm exec tsc --noEmit` from `proposedFrontend/` | Blocked | `proposedFrontend/node_modules` was missing, so pnpm attempted install. Registry access failed with `EACCES`, then symlink creation hit `EEXIST`. |
| `pnpm test` from `proposedFrontend/` | Blocked | Same missing dependency/network issue; command timed out while pnpm retried package downloads. |
| `pnpm build` from `proposedFrontend/` | Blocked | Same missing dependency/network issue; symlink creation hit `EBUSY`. |
| `git diff --check` | Passed | No whitespace errors. |

### Phase 1 Conclusion

The current backend and current frontend baseline are healthy. The proposed
frontend could not be validated in this sandbox because its dependencies were
not installed and registry access was blocked. The attempted pnpm commands
created an ignored `proposedFrontend/node_modules/` directory; reinstall
proposed frontend dependencies outside the sandbox before relying on proposed
frontend test/build results.

It is safe to proceed to Phase 2 after approval because Phase 1 changed only
documentation and did not alter runtime behavior.
