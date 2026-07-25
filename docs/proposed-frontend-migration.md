# Proposed Frontend Migration Baseline

Date: 2026-07-23

Scope: Phase 1 only. This document records the current migration baseline and
contract inventory for connecting `proposedFrontend/` to the existing backend.

## Applications Reviewed

- Current backend: `backend/app`
- Current production frontend: `frontend/`
- Proposed replacement frontend: `proposedFrontend/`
- Proposed frontend handoff contract:
  `proposedFrontend/docs/backend-api.openapi.yaml`

## Current Backend API Surface

Implemented backend routes detected during Phase 1:

- `GET /health`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/logout`
- `GET /account/status`
- `PUT /account/api-key`
- `GET /models/status`
- `POST /models/switch`
- `GET /components/capabilities`
- `GET /conversations`
- `POST /conversations`
- `GET /conversations/{conversation_id}`
- `PUT /conversations/{conversation_id}`
- `DELETE /conversations/{conversation_id}`
- `POST /conversations/import`
- `GET /conversations/export/all`
- `POST /chat`
- `POST /chat/stream`
- `POST /documents/upload`
- `POST /documents/{document_id}/process`
- `POST /documents/{document_id}/process/jobs`
- `POST /documents/{document_id}/index`
- `POST /documents/{document_id}/index/jobs`
- `POST /documents/search`
- `GET /documents`
- `GET /documents/indexes`
- `DELETE /documents/indexes/{collection_id}`
- `GET /documents/{document_id}`
- `GET /documents/{document_id}/chunks`
- `GET /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/cancel`
- `POST /repos/index-local`
- `POST /repos/index-local/vector`
- `POST /repos/ask`
- `POST /repos/search-vector`
- `GET /diagnostics/status`
- `GET /diagnostics/support-bundle`
- `GET /vectorstores/health`
- `GET /vectorstores/collections/export`
- `POST /vectorstores/collections/import`
- `POST /vectorstores/collections/migrate`

## Proposed Frontend Service Surface

`proposedFrontend/src/services/contracts.ts` defines:

- `AuthService`
- `ConversationService`
- `MessageService`
- `SourceService`
- `ProfileService`

The proposed frontend currently exports mock services only from
`proposedFrontend/src/services/index.ts`.

## Integration Gap Matrix

| Area | Proposed frontend expectation | Current backend reality | Phase 1 classification | Recommended path |
| --- | --- | --- | --- | --- |
| Runtime service selection | `VITE_USE_MOCK_API` switches mocks/HTTP | Implemented in Phase 4; mocks are default and HTTP mode returns not-connected errors | Backend not involved | Start real HTTP adapter methods in Phase 5 |
| API client | JSON client with bearer token | Current frontend also needs cookies, CSRF, FastAPI detail parsing, multipart, SSE | Adapter-only | Port current `frontend/src/api.js` behavior in Phase 3 |
| Login | `POST /auth/sign-in` returns `AuthSession` | `POST /auth/login` sets cookies and returns username session | Adapter-only initially | Map backend session to frontend session in Phase 5 |
| Session restore | `GET /auth/session` | `GET /auth/me` | Adapter-only | Map in Phase 5 |
| Logout | `POST /auth/sign-out` | `POST /auth/logout` with CSRF | Adapter-only | Map in Phase 5 |
| Signup/email verification | Email verification and account creation endpoints | Not implemented as real backend flow | Deferred/backend change | Disable or mock-only until product decision |
| OAuth | OAuth redirect endpoint | Not implemented | Deferred/backend change | Disable until auth roadmap |
| API key | Not central in proposed contracts | Required for chat/documents/repos/diagnostics | Frontend/backend bridge needed | Add account/API-key bridge in Phase 6 |
| Model/tool discovery | Static option lists in configuration modal | Real `/components/capabilities` endpoint | Adapter/UI change | Replace static lists in Phase 7 |
| Conversation list | Paged `Page<ConversationSummary>` | `ConversationListResponse` with `conversations` | Adapter-only | Map response in Phase 8 |
| Conversation create | `CreateConversationRequestDto` | Backend accepts full `ConversationRecord` | Adapter or backend alias | Adapter first in Phase 8/9 |
| Conversation rename | `PATCH /conversations/{id}/title` | Full-record `PUT /conversations/{id}` | Adapter-only initially | Load/update/upsert in Phase 10 |
| Conversation config | `PATCH /conversations/{id}/configuration` | Full-record `PUT /conversations/{id}` | Adapter-only initially | Load/update/upsert in Phase 10 |
| Chat non-streaming | `POST /conversations/{id}/messages` | `POST /chat` | Adapter-only | Map in Phase 11 |
| Chat streaming | `accepted/delta/complete/failed` events | `progress/metadata/token/done/error` events from `/chat/stream` | Adapter-only initially | Translate events in Phase 12 |
| Cancel/retry | Message cancel/retry endpoints | No direct chat cancel/retry endpoints; job cancel exists | Deferred/backend change | Defer or implement later if needed |
| Composer attachments | Pre-upload attachment endpoint | Backend supports image payloads in chat and documents separately | Mixed | Keep image/document distinction; defer general attachment endpoint |
| Sources | `SourceService` list/upload/delete/summary/retry | Backend documents, chunks, process/index jobs, search | Adapter plus possible backend delete gap | Map documents in Phases 14-15 |
| RAG source selection | `sourceIds` on conversation | Backend uses document IDs in RAG options and attachment IDs | Adapter-only | Map in Phase 16 |
| RAG metadata display | Sources in proposed source modal/messages | Backend returns source metadata, vector/rerank/compression warnings | UI/domain extension | Implement in Phase 17 |
| Profile | Rich profile load/update/avatar/export | Backend has account status/API key, not full profile | Deferred/backend change | Reconcile in Phase 18 |
| Repository tools | Not first-class in proposed service contracts | Backend has repo index/ask/vector routes | Frontend feature gap | Add in Phase 19 |
| Diagnostics | Not in proposed core contracts | Backend has diagnostics/status and support bundle | Frontend feature gap | Add in Phase 20 |
| Vector store diagnostics | Not in proposed core UI | Backend has vectorstore health/export/import/migrate | Frontend feature gap | Include with diagnostics/admin flow |

## Phase 1 Recommendation

Proceed with an adapter-first migration. The backend should remain the source
of truth. The proposed frontend should gain an HTTP service implementation that
maps existing backend routes and payloads into the proposed domain model. Add
backend compatibility endpoints only after adapter complexity proves they are
worth maintaining.

Do not replace `frontend/` until:

- Auth/session/API-key flow works in proposed frontend.
- Conversation persistence works.
- Streaming chat works.
- Document upload/process/index/search works.
- RAG metadata and source citations render.
- Repository and diagnostics features reach parity.
- Current and proposed frontend verification both pass.

## Phase 1 Verification Results

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

## Phase 1 Completion Notes

- No backend runtime code was changed.
- No current frontend runtime code was changed.
- `proposedFrontend/` remains side-by-side and mock-backed.
- `proposedFrontend/node_modules/` now exists from the attempted validation
  run, but it is ignored by `proposedFrontend/.gitignore`.
- Phase 2 should start with side-by-side workflow commands and dependency
  setup documentation, not HTTP adapter code.

## Phase 2 Side-by-Side Workflow

Phase 2 keeps the proposed frontend separate from the production frontend.

Added root commands:

- `make install-proposed-frontend`
- `make run-proposed-frontend`
- `make test-proposed-frontend`

Port plan:

- Current frontend: `http://localhost:5173`
- Proposed frontend: `http://localhost:8443`
- Backend: `http://localhost:8000`

Runtime behavior:

- The current production frontend remains unchanged.
- The proposed frontend remains mock-backed by default.
- `VITE_USE_MOCK_API=true` remains the documented proposed frontend default.
- Real HTTP adapter work is deferred to later phases.

Phase 2 does not replace `frontend/`, change backend routes, or connect the
proposed frontend to the backend.

## Phase 2 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `make help` | Blocked | `make` is not installed or not on `PATH` in this PowerShell shell. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py` | Passed | Backend smoke passed: 9 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `pnpm validate` from `proposedFrontend/` | Blocked | Proposed frontend dependencies are incomplete. pnpm attempted install, but registry access failed with `EACCES` and `fetch failed`. |

## Phase 2 Completion Notes

- The proposed frontend remains side-by-side and mock-backed.
- No backend runtime code changed.
- No current frontend runtime code changed.
- Root Makefile targets now document the intended workflow, but they must be
  executed in a shell with `make` installed.
- Before Phase 3 validation can fully exercise proposed frontend tests, run
  `make install-proposed-frontend` or `pnpm install --frozen-lockfile` from
  `proposedFrontend/` on a machine with registry access.

## Phase 3 API Client Hardening

Phase 3 changed only the proposed frontend API client and its focused tests.
It did not connect the proposed frontend to the backend yet.

Behavior added to `proposedFrontend/src/api/client.ts`:

- Cookie credentials are sent by default.
- Unsafe methods forward the readable CSRF cookie as `X-CSRF-Token`.
- Bearer token support and `X-Request-ID` behavior are preserved.
- JSON requests still serialize through `body`.
- Multipart uploads can use `formData` without overriding the browser
  `Content-Type` boundary.
- `204 No Content` and empty bodies return `undefined`.
- FastAPI error responses using `detail` strings or Pydantic validation arrays
  are normalized into `AppError`.

Focused tests were added in `proposedFrontend/src/api/client.test.ts` for:

- JSON serialization.
- HTTP error envelopes.
- Empty responses.
- FastAPI detail strings.
- FastAPI validation arrays.
- CSRF and credentials on unsafe requests.
- Multipart request handling.

## Phase 3 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `pnpm exec vitest run src/api/client.test.ts` from `proposedFrontend/` | Blocked | Proposed frontend dependencies are incomplete. pnpm attempted install, but registry access failed with `EACCES` and `fetch failed` before Vitest started. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py` | Passed | Backend smoke passed: 9 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | No whitespace errors; Windows reported expected LF-to-CRLF warnings on existing edited files. |

## Phase 3 Completion Notes

- No backend runtime code changed.
- No current frontend runtime code changed.
- Proposed frontend mocks remain the runtime default.
- Runtime service selection remains deferred to Phase 4.
- Proposed frontend test execution remains blocked until dependencies are
  installed with registry access.

## Phase 4 Runtime Service Selection

Phase 4 adds the runtime seam for choosing proposed frontend services.

Behavior added:

- `VITE_USE_MOCK_API` is now read by `proposedFrontend/src/services/index.ts`.
- Mocks remain the default when the variable is missing or any value other
  than explicit `false`.
- `VITE_USE_MOCK_API=false` selects
  `proposedFrontend/src/services/http/createHttpServices.ts`.
- The HTTP service factory currently returns clear `501` not-connected
  `AppError`s for every service method.
- No real backend endpoint mappings are implemented in Phase 4.

This intentionally creates a testable switch without claiming backend
integration is complete.

## Phase 4 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/index.test.ts src/api/client.test.ts` from `proposedFrontend/` | Passed | Focused proposed frontend suite passed: 2 files, 11 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py` | Passed | Backend smoke passed: 9 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | No whitespace errors; Windows reported expected LF-to-CRLF warnings on existing edited files. |

## Phase 4 Completion Notes

- No backend runtime code changed.
- No current frontend runtime code changed.
- Proposed frontend mocks remain the default runtime.
- HTTP mode is selectable but intentionally returns not-connected errors.
- Real auth/backend mapping remains deferred to Phase 5.
- Focused proposed frontend tests and TypeScript checks pass.

## Phase 5 Auth Adapter Compatibility

Phase 5 connects only the proposed frontend auth service to the existing
backend auth routes.

Implemented mappings:

- `AuthService.signIn` -> `POST /auth/login`
- `AuthService.restoreSession` -> `GET /auth/me`
- `AuthService.signOut` -> `POST /auth/logout`

Adapter behavior:

- Backend `{ username }` responses are converted into proposed `AuthSession`
  objects.
- The proposed `accessToken` is intentionally an empty string because the
  backend auth route is cookie-backed; API-key support is a separate Phase 6
  concern.
- `401` restore-session responses become `null` instead of throwing.
- Signup, email verification, account creation, and OAuth remain explicit
  `501` not-connected operations.

## Phase 5 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/index.test.ts src/api/client.test.ts` from `proposedFrontend/` | Passed | Proposed focused suite passed: 3 files, 16 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py` | Passed | Backend smoke/auth suite passed: 16 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |

## Phase 5 Completion Notes

- No backend runtime code changed.
- No current frontend runtime code changed.
- Proposed frontend HTTP mode now supports real backend login/session/logout.
- Proposed frontend mock mode remains the default.
- API-key/account bridging remains deferred to Phase 6.

## Phase 6 API Key and Account Bridge

Phase 6 adds a proposed frontend account service boundary for the existing
backend API-key workflow.

Implemented service contract:

- `account.getStoredApiKey()`
- `account.setStoredApiKey(apiKey)`
- `account.getStatus(apiKey?)`
- `account.updateApiKey(apiKey)`

Implemented HTTP mappings:

- `account.getStatus` -> `GET /account/status`
- `account.updateApiKey` -> `PUT /account/api-key`

Adapter behavior:

- Stored API keys use the compatibility localStorage key
  `local-ai-coding-assistant.api-key`.
- `getStatus` sends the stored or supplied key as `Authorization: Bearer`.
- `updateApiKey` sends `{ api_key }` to the backend and stores the key locally
  only after the backend accepts it.
- The proposed `AuthSession.accessToken` remains empty because backend login is
  cookie-backed; AI/data adapters should read the account API-key boundary in
  later phases.

## Phase 6 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/apiKeyStorage.test.ts src/services/mock/createMockServices.test.ts src/services/index.test.ts` from `proposedFrontend/` | Passed | Proposed focused suite passed: 4 files, 25 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py` | Passed | Backend smoke/auth/account suite passed: 18 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |

## Phase 6 Completion Notes

- No backend runtime code changed.
- No current frontend runtime code changed.
- Proposed frontend mock mode remains the default.
- Proposed frontend HTTP mode now supports account status and API-key updates.
## Phase 7 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/capabilities.test.ts src/services/http/createHttpServices.test.ts src/services/mock/createMockServices.test.ts src/features/configuration/ChatConfigurationModal.test.tsx src/services/index.test.ts` from `proposedFrontend/` | Passed | Proposed focused suite passed: 5 files, 29 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 17 files, 66 tests. First parallel attempt timed out at 120 seconds; rerun with a longer timeout passed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py` | Passed | Backend smoke/auth/account/capability suite passed: 18 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 7 Completion Notes

- Capability discovery is now connected in proposed frontend HTTP mode through
  `GET /components/capabilities`.
- Mock mode exposes deterministic capability fixtures and remains the default.
- Chat configuration options now come from capability data instead of hardcoded
  model/tool arrays.
- New unsaved conversations can adopt the first available discovered capability
  as their model/tool default once discovery has loaded.
- Unavailable tools are shown as disabled options, so users can see what the
  backend detected without selecting unusable capabilities.

## Phase 8 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/features/conversations/ConversationSidebar.test.tsx src/services/index.test.ts` from `proposedFrontend/` | Passed | Focused Phase 8 suite passed: 3 files, 16 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 18 files, 70 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py tests\\test_conversations.py` | Passed | Backend smoke/auth/account/capability/conversation suite passed: 27 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 8 Completion Notes

- Proposed frontend HTTP mode now maps conversation `list`, `get`, `create`,
  and `delete` to the backend `/conversations` API.
- Temporary conversations remain local-only in HTTP mode and are omitted from
  backend list persistence.
- Proposed-created records store proposed-only fields under
  `metadata.proposedFrontend`.
- Older backend records load with safe defaults until the full Phase 9 shape
  migration is implemented.
- Initial App loading now lets conversation history load even while the HTTP
  source/document adapter remains deferred.

## Phase 9 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/conversationMapper.test.ts src/services/http/createHttpServices.test.ts src/features/conversations/ConversationSidebar.test.tsx` from `proposedFrontend/` | Passed | Focused Phase 9 suite passed: 3 files, 15 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 73 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py tests\\test_conversations.py` | Passed | Backend smoke/auth/account/capability/conversation suite passed: 27 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 9 Completion Notes

- Conversation shape conversion now lives in
  `src/services/http/conversationMapper.ts`.
- Backend messages, statuses, attachments, settings, metadata, source IDs,
  system prompt, and temporary flags map into proposed frontend domain objects.
- Proposed-created records continue to store proposed-only fields under
  `metadata.proposedFrontend`.
- Legacy/partial backend records load with safe defaults and invalid messages
  are skipped.
- `chunker` and `ragPipeline` are preserved on `ModelConfiguration` for later UI
  and chat adapter phases.

## Phase 10 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 10 suite passed: 3 files, 30 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 76 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py tests\\test_conversations.py` | Passed | Backend smoke/auth/account/capability/conversation suite passed: 27 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. First attempt used a mistyped workdir and failed before running Vite; rerun with the correct path passed. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 10 Completion Notes

- Proposed frontend HTTP mode now persists conversation rename through
  `PUT /conversations/{id}`.
- Conversation configuration saves now persist system prompt, model settings,
  source IDs, and temporary flag through the same backend record update path.
- Updates preserve existing backend metadata and only replace
  `metadata.proposedFrontend`.
- Temporary conversations remain local-only for rename and configuration edits.
- Chat send/stream remain deferred to Phase 11 and Phase 12.

## Phase 11 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 11 suite passed: 3 files, 32 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 78 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py tests\\test_conversations.py tests\\test_chat.py` | Passed | Backend health/auth/account/capability/conversation/chat suite passed: 77 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 11 Completion Notes

- Proposed frontend HTTP `MessageService.send` now calls backend `POST /chat`.
- The chat request includes conversation history, conversation settings, and
  attachment document IDs.
- Stored API keys are forwarded as bearer tokens when configured.
- Backend `ChatResponse.answer` is converted into a proposed assistant
  `ChatMessage`.
- The current proposed UI uses `MessageService.stream`, so Phase 11 includes a
  non-SSE wrapper that emits accepted and complete events from the one-shot chat
  response.
- Transcript changes are held in memory only; durable message persistence
  remains Phase 13.

## Phase 12 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 12 suite passed: 3 files, 34 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 80 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py tests\\test_conversations.py tests\\test_chat.py` | Passed | Backend health/auth/account/capability/conversation/chat suite passed: 77 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 12 Completion Notes

- Proposed frontend HTTP `MessageService.stream` now calls backend
  `POST /chat/stream`.
- Backend `token` SSE events map to proposed `delta` events.
- Backend `done` SSE events map to completed assistant messages.
- Backend `error` SSE events and premature disconnects map to failed assistant
  messages.
- Stream requests forward stored API keys and CSRF headers.
- Durable transcript persistence remains Phase 13.

## Phase 13 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 13 suite passed: 3 files, 35 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 81 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_health.py tests\\test_component_capabilities.py tests\\test_login.py tests\\test_account.py tests\\test_conversations.py tests\\test_chat.py` | Passed | Backend health/auth/account/capability/conversation/chat suite passed: 77 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 13 Completion Notes

- Proposed frontend HTTP chat now persists completed or failed message exchanges
  by updating the backend conversation record after generation.
- Non-streaming `MessageService.send` persists the user and assistant messages
  after `/chat` succeeds.
- Streaming `MessageService.stream` persists the accepted user message and final
  assistant state after `/chat/stream` completes or fails.
- Temporary conversations remain local-only.
- If transcript persistence fails after generation, the local adapter cache keeps
  the transcript and the completed answer still returns.
- No new backend endpoints or database schema changes were added.

## Phase 14 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 14 suite passed: 3 files, 38 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully after adding the document mapper date helper. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 84 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_documents.py tests\\test_jobs.py tests\\test_chat.py` | Passed | Backend document/job/chat regression suite passed: 79 passed, 1 skipped because `ocrmypdf` is not installed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 14 Completion Notes

- Proposed frontend HTTP `SourceService.list` now reads backend documents for
  the active conversation.
- Proposed frontend HTTP `SourceService.upload` now uploads source files through
  backend `POST /documents/upload`.
- Source summaries now use the first extracted chunks from
  `GET /documents/{id}/chunks` when available.
- Backend document status values are normalized into proposed source status
  values.
- Source upload validation now matches the backend-supported document types.
- Source delete/retry and job-backed process/index progress remain deferred to
  later phases because the current backend document API does not expose delete
  or retry operations.

## Phase 15 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 15 suite passed: 3 files, 40 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 86 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_documents.py tests\\test_jobs.py tests\\test_chat.py` | Passed | Backend document/job/chat regression suite passed: 79 passed, 1 skipped because `ocrmypdf` is not installed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 15 Completion Notes

- Proposed frontend HTTP source uploads now start backend document process and
  index jobs after staging files.
- The adapter polls `/jobs/{id}` until process/index jobs reach a terminal
  state.
- Successful indexing returns sources as `ready`.
- Failed process/index jobs return sources as `failed` with the backend job
  error or message.
- `SourceService.retry` now re-runs the same process/index job sequence for an
  existing backend document.
- The existing upload progress indicator remains the minimal progress surface;
  richer per-job progress display is deferred.

## Phase 16 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 16 suite passed: 3 files, 43 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 89 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_chat.py tests\\test_documents.py tests\\test_jobs.py` | Passed | Backend chat/document/job regression suite passed: 79 passed, 1 skipped because `ocrmypdf` is not installed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 16 Completion Notes

- Proposed frontend HTTP chat requests now map selected conversation sources to
  backend `ragOptions.documentIds`.
- Ready composer document attachments remain in `attachmentDocumentIds` and are
  also included in RAG document IDs.
- Duplicate selected/attached document IDs are removed before sending.
- Chat requests with no selected or attached sources still omit `ragOptions` so
  plain chat behavior is preserved.
- Backend source citation metadata is not rendered yet; that remains Phase 17.

## Phase 17 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/mock/createMockServices.test.ts src/features/chat/ChatTranscript.test.tsx` from `proposedFrontend/` | Passed | Focused Phase 17 suite passed: 4 files, 49 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 90 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_chat.py tests\\test_documents.py tests\\test_jobs.py` | Passed | Backend chat/document/job regression suite passed: 79 passed, 1 skipped because `ocrmypdf` is not installed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 17 Completion Notes

- Proposed frontend chat messages can now carry backend RAG, rerank,
  compression, warning, and source citation metadata.
- HTTP non-streaming and streaming chat adapters attach metadata to completed
  assistant messages.
- Conversation persistence preserves message metadata so citations survive
  reloads.
- Chat transcript renders source number, document name, page, final rank,
  vector score, rerank score, text preview, and RAG/rerank/compression warnings.
- Messages without metadata continue to render as before.

## Phase 18 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/features/profile/ProfilePage.test.tsx src/services/mock/createMockServices.test.ts` from `proposedFrontend/` | Passed | Focused Phase 18 suite passed: 3 files, 48 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 19 files, 93 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_account.py tests\\test_login.py tests\\test_browser_session_flow.py` | Passed | Backend account/auth/session regression suite passed: 11 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 18 Completion Notes

- Proposed frontend profile services now distinguish prototype profile behavior
  from HTTP backend reality.
- HTTP profile loading derives backend-backed account fields from `/auth/me` and
  `/account/status`.
- HTTP profile edits are browser-local presentation preferences.
- Avatar upload is disabled in HTTP mode because the backend has no avatar API.
- Profile export in HTTP mode includes local profile data and support metadata
  that identifies what is backend-backed, browser-local, or unsupported.
- Mock mode keeps its richer local profile/avatar behavior for design and test
  coverage.

## Phase 19 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/mock/createMockServices.test.ts src/features/repositories/RepositoryPage.test.tsx src/features/conversations/ConversationSidebar.test.tsx` from `proposedFrontend/` | Passed | Focused Phase 19 suite passed after one test assertion fix: 4 files, 45 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 20 files, 95 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_repositories.py tests\\test_chat.py tests\\test_vector_indexes.py` | Passed | Backend repository/chat/vector regression suite passed: 67 passed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 19 Completion Notes

- Proposed frontend now has a repository service boundary in mock and HTTP
  modes.
- HTTP mode maps repository workflows to the existing backend repository APIs:
  keyword index, vector index, keyword ask, and vector search.
- Added a protected Repositories page and account-menu navigation entry.
- The UI surfaces repository path/request errors, stale freshness warnings,
  keyword-RAG sources, vector result scores, file paths, line ranges, language,
  and symbol metadata when available.
- No backend repository API changes were required.

## Phase 20 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/mock/createMockServices.test.ts src/features/diagnostics/DiagnosticsPage.test.tsx src/features/conversations/ConversationSidebar.test.tsx` from `proposedFrontend/` | Passed | Focused Phase 20 suite passed after one assertion fix: 4 files, 48 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_diagnostics.py tests\\test_health.py tests\\test_account.py` | Passed | Backend diagnostics, health, and account regression suite passed: 7 passed. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 21 files, 99 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 20 Completion Notes

- Proposed frontend now has a diagnostics service boundary in mock and HTTP
  modes.
- HTTP mode maps diagnostics to `/diagnostics/status` and
  `/diagnostics/support-bundle`.
- Mock mode exposes deterministic runtime, model, document, retrieval, and job
  diagnostics for hermetic testing.
- Added a protected Diagnostics page and account-menu navigation entry.
- The UI preserves support-bundle redaction messaging and exports redacted JSON
  without showing sensitive raw content inline.
- No backend diagnostics API changes were required.

## Phase 21 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run src/features/conversations/ConversationSidebar.test.tsx src/features/repositories/RepositoryPage.test.tsx src/features/diagnostics/DiagnosticsPage.test.tsx src/features/profile/ProfilePage.test.tsx src/features/settings/SettingsPage.test.tsx` from `proposedFrontend/` | Passed | Focused Phase 21 workflow suite passed: 5 files, 14 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_chat.py tests\\test_documents.py tests\\test_repositories.py tests\\test_diagnostics.py tests\\test_account.py` | Passed | Backend audited-surface regression suite passed: 84 passed, 1 skipped because `ocrmypdf` is not installed. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 21 files, 100 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported expected LF-to-CRLF working-copy warnings for `Makefile`, `docs/setup.md`, and `docs/testing.md`. |

## Phase 21 Completion Notes

- Added `docs/proposed-frontend-parity-report.md` as the Phase 21 feature
  parity report.
- Audited migrated user-facing workflows against the current frontend: auth,
  account/API key, conversations, chat, settings, document/job flows, RAG source
  metadata, repositories, diagnostics, profile, and navigation.
- Fixed a small account-menu parity gap so Help navigates to `/help` instead
  of showing a transient notice.
- Added account-menu workflow test coverage for Profile, Repositories,
  Diagnostics, Settings, Help, and Log out.
- Deferred Help content, password reset, email-only signup completion, and
  backend adapter cleanup to later planned phases.

## Phase 22 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_account.py tests\\test_repositories.py` | Passed | Targeted backend compatibility suite passed: 9 tests. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run src/services/http/createHttpServices.test.ts src/services/http/conversationMapper.test.ts src/services/index.test.ts` from `proposedFrontend/` | Passed | Focused proposed service suite passed: 3 files, 38 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_account.py tests\\test_repositories.py tests\\test_chat.py tests\\test_documents.py tests\\test_diagnostics.py` | Passed | Backend compatible-route regression suite passed: 86 passed, 1 skipped because `ocrmypdf` is not installed. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 21 files, 100 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `node scripts\\lint-check.mjs` from `frontend/` | Passed | Current frontend lint guard passed for 46 files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` | Passed | Current frontend production build succeeded. |
| `git diff --check` | Passed | Exit code 0; Git reported LF-to-CRLF working-copy warnings for touched text files. |

## Phase 22 Completion Notes

- Added non-breaking backend request aliases for proposed frontend compatibility:
  `apiKey` on `PUT /account/api-key` and `repoName` on `POST /repos/ask`.
- Preserved existing legacy request bodies, response shapes, auth behavior, and
  route paths.
- Updated the proposed HTTP adapter to send the new camelCase request fields.
- Added backend route compatibility tests for both aliases.
- Added `docs/frontend-backend-contract.md` to document why response
  normalization remains frontend-side until a future API-versioning decision.
- No broader backend alias layer or versioned API route was introduced.

## Phase 23 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\eslint.cmd .` from `proposedFrontend/` | Failed, then passed | Initial promoted lint path exposed diagnostics-page lint issues. After fixes, ESLint passed. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full promoted frontend suite passed: 21 files, 100 tests. Run outside sandbox because sandboxed Vite setup-file path resolution failed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Promoted frontend production build succeeded. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed: 185 passed, 7 skipped for optional OCR/Ollama/Chroma checks. |
| `docker compose -f docker-compose.test.yml config` | Passed | Docker test Compose config resolves `frontend-test` from `proposedFrontend/Dockerfile.test`. Run with escalation because Docker config is outside the workspace sandbox. |
| `docker compose config` | Passed after follow-up | Initially blocked by missing local `backend/.env`; resolved by copying the safe ignored `backend/.env.example` template. |
| `docker compose -f docker-compose.prod.yml config` | Passed after follow-up | Initially blocked by missing local `backend/.env`; resolved by copying the safe ignored `backend/.env.example` template. |
| `docker build --progress=plain -t local-ai-proposed-frontend-phase23 .` from `proposedFrontend/` | Passed after follow-up | Initial direct build revealed missing `proposedFrontend/.dockerignore`; after adding it, the promoted frontend image built successfully. |
| `docker compose build frontend` | Passed after follow-up | Default Compose successfully built the promoted frontend service from `proposedFrontend/`. |
| `make -n test-frontend` and `make -n run-frontend` | Blocked | `make` is not installed in this PowerShell environment. Underlying target commands were run directly instead. |
| `git diff --check` | Passed | Exit code 0; Git reported LF-to-CRLF working-copy warnings for touched text files. |

## Phase 23 Completion Notes

- Promoted `proposedFrontend/` to the production frontend build target.
- Default Compose, production Compose, Docker test Compose, CI, setup/start
  scripts, and Makefile frontend targets now point at `proposedFrontend/`.
- Added proposed frontend Docker and Nginx files for production and test images.
- Production/Docker builds set `VITE_USE_MOCK_API=false`; frontend-only mock
  demos can still opt in with `VITE_USE_MOCK_API=true`.
- Legacy `frontend/` remains in place and is available through explicit legacy
  Makefile targets; it was not deleted or moved.
- Follow-up blocker resolution added `proposedFrontend/.dockerignore` so Docker
  does not copy local `node_modules` into the image.
- Default/prod/test Compose config and the promoted frontend Docker build now
  pass in this environment.

## Phase 24 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed: 185 passed, 7 skipped for optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma checks. |
| `.\\node_modules\\.bin\\oxfmt.cmd --check .` from `proposedFrontend/` | Failed, then passed | Initial formatter check found existing formatting drift. Running the formatter exposed a formatter-sensitive inline object type in one test; the test now uses interfaces and the final format check passed. |
| `.\\node_modules\\.bin\\eslint.cmd .` from `proposedFrontend/` | Passed | Proposed frontend ESLint completed successfully after the formatter-safe test update. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 21 files, 100 tests. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.\\node_modules\\.bin\\playwright.cmd test --config playwright.config.ts` from `proposedFrontend/` | Passed | Chromium e2e suite passed: 6 tests. Run with escalation because browser/test-server orchestration runs outside the workspace sandbox. |
| `docker compose config` | Passed | Default Compose config resolves the promoted frontend service from `proposedFrontend/`. |
| `docker compose -f docker-compose.prod.yml config` | Passed | Production Compose config resolved with safe defaults. |
| `docker compose -f docker-compose.test.yml config` | Passed | Test Compose config resolved with backend and frontend test services. |
| `docker compose build frontend` | Passed | Default promoted frontend Docker image built successfully. |
| `docker compose -f docker-compose.test.yml build frontend-test` | Passed | Frontend test image built successfully. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | Dockerized backend test suite passed: 150 passed, 6 skipped. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test sh -c "pnpm lint --quiet && pnpm typecheck && pnpm exec vitest run --reporter=dot && pnpm build"` | Failed, then passed | Initial Docker frontend run timed out in a long repository workflow test. After giving that integration-style test a 15-second timeout, the Docker frontend suite passed: 21 files, 100 tests, plus production build. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_ollama_smoke.py tests\\test_live_ollama.py -m ollama` | Passed with skips | Five optional live Ollama tests skipped cleanly because `RUN_OLLAMA_TESTS=1` was not set. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Temporary Docker test network was removed. |

## Phase 24 Completion Notes

- Phase 24 proved the promoted frontend wiring locally and in Docker without
  adding new product features.
- The only code changes were test-maintenance fixes: a larger timeout for one
  Docker-slow repository workflow test and formatter-safe helper interfaces in
  the HTTP service test.
- Optional live Ollama smoke remains opt-in and is not part of the hermetic
  default or Docker test suites.
- No Phase 25 public-release polish work was started.

## Phase 25 Verification Results

| Command | Result | Notes |
| --- | --- | --- |
| `rg -n "frontend/|proposedFrontend|legacy frontend|old frontend|not implemented|coming soon|future" README.md docs CHANGELOG.md mitigationPlan.md` | Passed | Identified stale or context-sensitive release wording before final documentation updates. Remaining historical roadmap/log entries are intentional. |
| Documentation review | Passed | README, changelog, release checklist, backup/restore, dependency review, setup, testing, and deployment hardening docs were reviewed for promoted-frontend accuracy. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed: 185 passed, 7 skipped. |
| `.\\node_modules\\.bin\\oxfmt.cmd --check .` from `proposedFrontend/` | Passed | Promoted frontend format check passed. |
| `.\\node_modules\\.bin\\eslint.cmd .` from `proposedFrontend/` | Passed | Promoted frontend ESLint completed successfully. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Promoted frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Promoted frontend production build succeeded. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Failed, then passed | First full run timed out; focused profile rerun passed, then full suite passed with 21 files and 100 tests using a longer command timeout. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |

## Phase 25 Completion Notes

- Public release copy now describes `proposedFrontend/` as the production
  frontend and `frontend/` as archived legacy code.
- README includes a manual local smoke path for backend plus promoted frontend
  validation.
- Changelog and release checklist now reflect completed frontend Vitest,
  Playwright, Docker test, image build, and Compose config verification.
- Backup/restore and dependency-review docs now include the promoted frontend
  paths and pnpm workflow.
- The frontend migration plan is complete; no Phase 26/new feature work was
  started.
