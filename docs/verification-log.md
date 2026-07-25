# Verification Log

This log records stabilization checks before starting future roadmap phases.

## Phase 1 Baseline Stabilization

Date: 2026-07-02

Scope:

- Establish a trusted baseline for the current branch.
- Run local and Dockerized verification commands where available.
- Record blockers clearly instead of treating unavailable tools as passing.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short` | Passed | Working tree was clean before Phase 1 documentation was added. |
| `Get-Command python -ErrorAction SilentlyContinue` | Blocked | No `python` executable was available on `PATH` in this shell. |
| `Get-Command npm -ErrorAction SilentlyContinue` | Blocked | No `npm` executable was available on `PATH` in this shell. |
| `Test-Path .venv\Scripts\python.exe` | Blocked | No project virtual environment was present. |
| `Test-Path frontend\node_modules` | Blocked | Frontend dependencies were not installed locally. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m pytest --version` | Blocked | Bundled Python is available, but `pytest` is not installed in that runtime. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts/lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 37 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe frontend/node_modules/vitest/vitest.mjs --version` | Blocked | Vitest is unavailable because `frontend/node_modules` is missing. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall backend/app tests scripts` | Passed | Python source files compiled successfully. This is a syntax check, not a substitute for pytest. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | 73 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test` | Failed, then passed | First run failed because `NavigationRail` used a date-sensitive test fixture. After updating the fixture and rebuilding `frontend-test`, the suite passed: 7 files passed, 33 tests passed, production build passed. |
| `docker compose -f docker-compose.test.yml build frontend-test` | Passed | Rebuilt the frontend test image so it included the updated fixture. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Test network was removed after verification. |
| `docker compose build backend` | Blocked | Compose requires `backend/.env`, which was not present in this checkout. |
| `docker build ./backend` | Passed | Production backend Dockerfile built successfully and installed `ocrmypdf`, `pdfplumber`, and `pymupdf`. |

### Current Baseline Status

Phase 1 baseline verification is complete through Docker. Local `make
test-backend` and `make test-frontend` remain unavailable in this shell because
local Python/npm dependencies are not installed, but the Dockerized backend and
frontend suites both pass from clean test images.

### Notes

- `docker compose build backend` could not be used because Compose requires
  `backend/.env`. The equivalent Dockerfile build was verified with
  `docker build ./backend`.
- The frontend test fixture in
  `frontend/src/components/__tests__/workspace-components.test.jsx` now uses
  the current runtime date so the recents grouping test is not tied to a stale
  calendar date.

### Phase 1 Verification Checklist

- [x] Python source compiles successfully
- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Frontend lint guard passes
- [x] Documentation updated with verification results
- [x] No new critical or high-severity issues introduced
- [x] Docker backend builds with OCR/PDF requirements
- [x] Verification results are complete

## Phase 2 Documentation and API Contract Alignment

Date: 2026-07-02

Scope:

- Align API, architecture, and setup documentation with current routers,
  schemas, and implemented behavior.
- Clearly document per-chat settings, component discovery, document endpoints,
  RAG metadata, reranking, compression, and known fallback/discovery-only
  areas.
- Do not implement Phase 3 capability metadata changes.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `rg "Switch Models\|Use installed model\|Refresh local models\\b\|Chat always uses the active model\|keyword-only\|node:test\|future upload\|hidden from the dashboard\|Phase 9" docs README.md -n` | Passed | Only current `Refresh local models/tools` wording remains. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m compileall backend/app tests scripts` | Passed | Python source files compiled successfully. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts/lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 37 frontend files. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | 73 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `docker compose -f docker-compose.test.yml build frontend-test` | Passed | Frontend test image rebuilt successfully. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test` | Passed | 7 test files passed, 33 tests passed, production build passed. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Test network was removed after verification. |

### Phase 2 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] API docs match implemented routers and schemas
- [x] Architecture/setup docs distinguish implemented, fallback, and planned features

## Phase 3 Capability Metadata Contract

Date: 2026-07-02

Scope:

- Add additive execution metadata to `/components/capabilities` entries.
- Distinguish implemented, fallback, discovery-only, placeholder, and
  unavailable capabilities without changing existing selection behavior.
- Preserve existing chat, document, RAG, reranking, compression, and
  `/models/status` behavior.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_component_capabilities.py` | Passed | 6 passed. |
| `.venv\Scripts\python.exe -m compileall backend\app tests scripts` | Passed | Python source and tests compiled successfully. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 75 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 37 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 7 test files passed, 33 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |

### Phase 3 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Capability metadata is additive and preserves existing IDs/categories

## Phase 4 Frontend Capability Metadata Display

Date: 2026-07-02

Scope:

- Display Phase 3 capability execution metadata in the existing per-chat
  Conversation Settings controls.
- Keep the UI backward-compatible with older capability entries that do not
  include metadata.
- Do not change selected settings, backend execution, document/RAG behavior,
  or introduce Phase 5 functionality.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src\components\AccountPanel.conversation-settings.test.jsx` from `frontend/` | Passed | 3 tests passed after simplifying status markup. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 75 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 37 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 7 test files passed, 34 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |

### Phase 4 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Capability metadata display is read-only and preserves settings behavior

## Phase 5 Repository Hygiene Guard

Date: 2026-07-02

Scope:

- Remove tracked local virtualenv artifacts from the git index while keeping
  the local `.venv` available on disk.
- Add an automated guard that fails if tracked files match `.gitignore`.
- Check the 15-phase roadmap into `docs/development-roadmap.md` before future
  phase work continues.
- Do not change runtime behavior, API behavior, UI behavior, or begin Phase 6.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `git ls-files -ci --exclude-standard \| Measure-Object` | Passed | Confirmed 1,948 tracked ignored files before cleanup. |
| `git rm -r --cached .venv` | Passed | Removed `.venv` from the git index only; local files remained on disk. |
| `.venv\Scripts\python.exe --version` | Passed | Local Windows venv still launches: Python 3.12.13. |
| `git ls-files -ci --exclude-standard \| Measure-Object` | Passed | Confirmed 0 tracked ignored files after cleanup. |
| `.venv\Scripts\python.exe -m pytest tests\test_repository_hygiene.py` | Passed | 1 passed. |
| `rg -n "Development roadmap\|development-roadmap" README.md docs\development-roadmap.md` | Passed | README links to the checked-in roadmap artifact. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 76 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 37 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 7 test files passed, 34 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |

### Phase 5 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] No tracked files match `.gitignore`
- [x] 15-phase roadmap is checked into the repository

## Phase 6 CI and Repeatable Verification

Date: 2026-07-02

Scope:

- Add GitHub Actions for backend tests.
- Add GitHub Actions for frontend lint, tests, and production build.
- Add manual Docker verification workflow.
- Keep live Ollama tests opt-in and skipped by default.
- Do not begin Phase 7 frontend state decomposition.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `Test-Path .github\workflows\ci.yml; Test-Path .github\workflows\docker-verification.yml` | Passed | Both workflow files are present. |
| `rg -n "RUN_OLLAMA_TESTS\|python -m pytest\|npm ci\|npm run lint\|npm run test:run\|npm run build\|workflow_dispatch" .github\workflows docs\testing.md README.md` | Passed | Confirmed default CI commands, manual Docker trigger, and Ollama skip setting. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 76 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 37 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 7 test files passed, 34 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. |

### Phase 6 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] CI workflow files are present and default CI does not require Ollama

## Phase 7 Frontend State Decomposition

Date: 2026-07-02

Scope:

- Extract capability loading and refresh state from `App.jsx` into a focused hook.
- Preserve existing account panel capability status messages and refresh behavior.
- Add hook-level tests for capability loading, failure, pending, and reset states.
- Do not begin Phase 8 backend service boundary cleanup.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src/hooks/useCapabilities.test.js` from `frontend/` | Passed | 1 test file passed, 5 tests passed. Initial sandboxed attempt failed while loading Vitest config due restricted file access, then passed unsandboxed. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 76 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 test files passed, 39 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported the existing CRLF normalization warning for `frontend/src/App.jsx`. |

### Phase 7 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] No user-facing workflow regressions

## Phase 8 Backend Service Boundary Cleanup

Date: 2026-07-02

Scope:

- Rename backend AI scaffold modules from `stubs.py` to explicit
  `unavailable.py` adapter modules.
- Preserve existing exported unavailable adapter class names for compatibility.
- Make component provider protocols runtime-checkable and documented.
- Replace stale backend execution messages that referenced "this phase" with
  adapter-boundary messages.
- Document service/provider ownership in the architecture guide.
- Do not begin Phase 9 document pipeline hardening.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_ai_provider_boundaries.py` | Passed | 5 provider-boundary tests passed. |
| `rg -n "from app\.ai\..*\.stubs\|stubs\.py\|not implemented in this phase" backend/app tests docs README.md` | Passed | No stale backend/test references remained. The only match is the roadmap text explaining Phase 8's original problem. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 81 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 test files passed, 39 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 8 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Service ownership is clearer than before

## Phase 9 Document Pipeline Hardening

Date: 2026-07-02

Scope:

- Harden document processing for empty extracted text.
- Harden chunk artifact reads and indexing when artifacts are malformed.
- Add metadata identity consistency checks for stored document artifacts.
- Add API tests for missing originals, malformed metadata, malformed chunks,
  empty text, and indexing failures.
- Document the safer document artifact failure behavior.
- Do not begin Phase 10 retrieval quality and source reliability work.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_documents.py tests\test_vector_indexes.py` | Passed | 25 document/vector tests passed. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 86 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 test files passed, 39 tests passed. React printed existing `act(...)` warnings in the accessibility suite. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 9 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Document failures are safe and explainable

## Phase 10 Retrieval Quality and Source Reliability

Date: 2026-07-02

Scope:

- Normalize retrieved source metadata before prompt injection and response
  payloads.
- Skip empty retrieved chunks with a RAG warning.
- Include `collectionId` in chat source payloads when available.
- Add backend tests for sparse source metadata, skipped empty chunks, source
  numbering, and collection IDs.
- Add frontend test coverage for source chips that include long document names
  and rerank score labels.
- Document source numbering, scoring fields, preview behavior, and limits.
- Do not begin Phase 11 vector store adapter work.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_chat.py` | Passed | 25 chat/RAG tests passed after fixing test fixtures to corrupt stored vector artifacts directly. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src/components/__tests__/workspace-components.test.jsx` from `frontend/` | Passed | 1 test file passed, 8 tests passed. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 88 passed, 4 skipped. Optional live Ollama tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 test files passed, 40 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 10 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Source metadata remains stable across RAG modes

## Phase 11 Real Vector Store Adapter Layer

Date: 2026-07-02

Scope:

- Add a vector store backend protocol and adapter health metadata.
- Keep `JsonVectorStore` as the default active backend.
- Add `VectorStoreManager` for backend selection and JSON fallback behavior.
- Add an optional `ChromaVectorStore` adapter behind the `chromadb` package and
  `VECTOR_STORE_BACKEND=chroma`.
- Update component discovery with vector adapter health and JSON fallback
  metadata.
- Add vector adapter selection and contract tests, including an optional Chroma
  contract test that skips when `chromadb` is missing.
- Document vector backend configuration and fallback behavior.
- Do not begin Phase 12 OCR expansion.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_vector_store_adapters.py tests\test_component_capabilities.py` | Passed | 11 tests passed after fixing staticmethod monkeypatching. |
| `.venv\Scripts\python.exe -m pytest tests\test_vector_store_adapters.py` | Passed | 5 passed, 1 skipped. Chroma contract skipped because `chromadb` is not installed. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 94 passed, 5 skipped. Optional live Ollama tests and optional Chroma contract skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 test files passed, 40 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 11 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] JSON store behavior remains the default and still passes tests

## Phase 12 OCR Expansion

Date: 2026-07-02

Scope:

- Add a PDF OCR provider interface with safe unavailable and execution errors.
- Add an OCRmyPDF provider for low-text PDF fallback when the `ocrmypdf`
  binary is installed and selected.
- Keep other OCR engines discoverable but unwired until provider adapters are
  added.
- Preserve normal PDF parsing when selectable text is sufficient.
- Surface OCR fallback warnings and selected engine metadata in document
  processing results.
- Do not begin Phase 13 vision chat.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_documents.py tests\test_component_capabilities.py` | Passed | 24 passed, 1 skipped. Optional OCRmyPDF smoke skipped because the binary is not installed. |
| `.venv\Scripts\python.exe -m pytest tests\test_component_capabilities.py` | Passed | 8 passed. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 97 passed, 6 skipped. Optional live Ollama, OCRmyPDF binary, and Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | Initial sandbox run failed because esbuild could not read a parent directory; rerun outside the sandbox passed with 8 test files and 40 tests. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 12 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Missing OCR tools never break document processing unexpectedly

## Phase 13 Vision Chat

Date: 2026-07-03

Scope:

- Add optional image attachments to chat requests.
- Validate image count, MIME type, base64 payload, and decoded byte size before
  sending image data to Ollama.
- Use the selected per-chat `visionModel` for image-bearing chat requests.
- Preserve the existing text-only chat path and provider call shape.
- Mark discovered Ollama vision models as implemented capabilities.
- Add frontend composer image attachment controls without redesigning the UI.
- Add optional live Ollama vision smoke coverage that skips unless explicitly
  enabled.
- Do not begin Phase 14 streaming responses.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_chat.py tests\test_component_capabilities.py tests\test_ollama_smoke.py` | Passed | 36 passed, 4 skipped. Live Ollama smoke tests skipped because `RUN_OLLAMA_TESTS=1` was not set. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src/api.test.js src/components/__tests__/workspace-components.test.jsx` from `frontend/` | Passed | Initial sandbox run failed because esbuild could not read a parent directory. First outside-sandbox run exposed a missing `File.arrayBuffer` fallback; rerun passed with 2 files and 16 tests. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 100 passed, 7 skipped. Optional OCRmyPDF, live Ollama, and Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 test files passed, 42 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 13 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Text-only chat remains unchanged

## Phase 14 Streaming Responses and Runtime Events

Date: 2026-07-03

Scope:

- Add Ollama streaming generation support while preserving complete
  non-streaming generation.
- Add `POST /chat/stream` as an authenticated server-sent-events endpoint.
- Emit `progress`, `metadata`, `token`, `done`, and `error` stream events.
- Update the frontend chat send path to render one assistant message as tokens
  arrive.
- Preserve the existing `/chat` response contract and metadata shape.
- Add backend, API, and integration tests for streaming success and failure.
- Do not begin Phase 15 release hardening.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_chat.py tests\test_ollama_service.py` | Passed | 38 passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src/api.test.js src/__tests__/app.integration.test.jsx src/components/__tests__/workspace-components.test.jsx` from `frontend/` | Passed | Initial run caught stream metadata/source fixture adjustments; final targeted run passed with 3 files and 25 tests. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 103 passed, 7 skipped. Optional OCRmyPDF, live Ollama, and Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 test files passed, 44 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 14 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Streaming failures degrade safely

## Phase 15 Production Hardening and Release Readiness

Date: 2026-07-03

Scope:

- Add release-readiness documentation for security posture, deployment
  hardening, backup/restore, dependency review, and release verification.
- Add a versioned changelog and root security policy.
- Add repository hygiene coverage for release-readiness documents.
- Ensure Docker backend tests include release documentation files.
- Create `roadmap_v2.md` with the next 15 development phases for the public
  release track.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_repository_hygiene.py` | Passed | 2 passed. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 104 passed, 7 skipped. Optional OCRmyPDF, live Ollama, and Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | Initial sandbox run failed due restricted parent-directory access for esbuild config resolution; outside-sandbox run passed with 8 files and 44 tests. Existing React `act(...)` warnings remain in the accessibility test output. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `npm audit --audit-level=high` from `frontend/` | Not run | No `npm` executable was available in this PowerShell environment; frontend dependency integrity was covered by installed lockfile tests, lint, and production build. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Passed | Rebuilt current Docker test images. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Failed, then passed | First rebuilt run found the new release docs were not copied into the backend test image. After updating `backend/Dockerfile.test`, rerun passed with 104 passed and 7 skipped. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test` | Passed | Frontend Docker lint, Vitest, and production build passed. |
| `make smoke-docker` | Not run | `make` is not installed in this PowerShell environment, so the target's commands were run manually. |
| `docker compose -f docker-compose.test.yml run --rm backend-test python -m pytest tests/test_health.py tests/test_component_capabilities.py` | Passed | 9 passed. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test npm run lint` | Passed | Frontend lint guard passed. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Test network was removed after verification. |

### Phase 15 Verification Checklist

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Release checklist, hardening docs, changelog, and roadmap v2 are present

## Roadmap v2 Phase 1 Release Candidate Stabilization

Date: 2026-07-03

Scope:

- Audit public release-candidate wording in `README.md`, `CHANGELOG.md`,
  `docs/setup.md`, release docs, and example configuration files.
- Keep Phase 1 limited to release-candidate documentation, safe defaults, and
  verification records.
- Refresh stale vector-backend wording so JSON is clearly the default and
  Chroma is described as an optional early adapter.
- Add a release-candidate checklist entry to `CHANGELOG.md`.
- Confirm example configuration files use placeholders, empty secrets, and
  trusted-network defaults.
- Do not begin Roadmap v2 Phase 2.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Frontend test runtime: bundled Node executable under
  `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`.
- Docker CLI was present, but the Docker daemon was not running.
- Vitest required an outside-sandbox rerun because esbuild could not read a
  parent directory inside the restricted filesystem sandbox.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `git status --short` | Passed | Working tree contained intentional Phase 1 docs/config changes only. |
| `rg -n "pytest 22\|node 5\|not wired yet\|temporarily hidden\|portfolio-grade\|external Chroma\|external vector database backends are not wired\|current phase\|future work\|coming soon\|TODO\|FIXME\|VECTOR_STORE_BACKEND=chroma\|VECTOR_STORE_BACKEND=json\|API_KEY=\|password\|secret" README.md CHANGELOG.md SECURITY.md docs .env.example backend/.env.example frontend/.env.example credentials.example.json app-settings.example.json` | Passed | Remaining matches were accurate limitations, safe placeholders, or security guidance. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 104 passed, 7 skipped. Optional OCRmyPDF, live Ollama, and Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 frontend files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Failed, then passed | Sandbox run failed due restricted esbuild/Vite config path access. Outside-sandbox rerun passed with 8 files and 44 tests. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Blocked | Docker daemon was not running: `open //./pipe/docker_engine: The system cannot find the file specified.` |
| `git ls-files -ci --exclude-standard` | Passed | No tracked ignored files were reported. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |

### Phase 1 Verification Checklist

- [x] Existing tests pass
- [x] Docker blocker documented
- [x] Release docs match current behavior
- [x] No stale "not implemented" claims for implemented features
- [x] No local secrets or generated data are tracked
- [x] Phase 2 was not started

## Roadmap v2 Phase 2 Server-Side Conversation Persistence

Date: 2026-07-03

Scope:

- Add optional backend conversation persistence while preserving browser
  localStorage as the default and fallback behavior.
- Store persisted conversations in user-scoped JSON files under
  `data/conversations/`.
- Add session-protected conversation create/list/read/update/delete,
  import, and export endpoints.
- Add browser-to-backend migration from Settings.
- Keep this phase below Phase 3 scope: no SQLite, no broad metadata migration
  layer, no cloud sync, and no multi-device sync.
- Update setup, architecture, API, backup/restore, README, env example, and
  changelog documentation.

### Storage Format

Phase 2 uses one JSON file per signed-in local username:

```text
data/conversations/{safe_username}.json
```

Each file contains a small object with `version`, `username`,
`conversations`, and `deletedConversationIds`. This remains simple,
inspectable, backup-friendly, and does not introduce Phase 3 database
migration work.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Frontend test runtime: bundled Node executable under
  `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`.
- Docker CLI was present, but the Docker daemon was not running.
- Vitest was run outside the restricted sandbox because esbuild/Vite config
  resolution requires normal filesystem access on this machine.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_conversations.py` | Passed | 9 passed. |
| `.venv\Scripts\python.exe -m pytest tests\test_conversations.py tests\test_repository_hygiene.py` | Passed | 11 passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src/api.test.js src/chatState.test.js src/components/AccountPanel.conversation-settings.test.jsx src/__tests__/app.integration.test.jsx` from `frontend/` | Passed | 4 files passed, 30 tests passed. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 113 passed, 7 skipped. Optional OCRmyPDF, live Ollama, and Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 files passed, 50 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Blocked | Docker daemon was not running: `open //./pipe/docker_engine: The system cannot find the file specified.` |
| `git ls-files -ci --exclude-standard` | Passed | No tracked ignored files were reported. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `git diff --check` | Passed | No whitespace errors. Git reported existing CRLF normalization warnings. |
| `rg -n "backend does not persist\|Conversations live in browser localStorage\|browser-local chat persistence$\|Phase 3\|SQLite\|database migration\|server-side chat persistence as separate work\|external vector database backends are not wired" README.md docs CHANGELOG.md backend frontend tests` | Passed | Matches were limited to historical roadmap/log references, not current Phase 2 behavior docs. |

### Phase 2 Verification Checklist

- [x] Backend conversation service unit tests pass
- [x] Conversation API tests pass
- [x] Corrupt and missing conversation store behavior is tested
- [x] Frontend migration and persistence behavior is tested
- [x] Browser-local fallback behavior remains the default and is tested
- [x] Backup/restore docs include backend-persisted conversations
- [x] Existing backend and frontend suites pass
- [x] Docker blocker documented
- [x] Phase 3 was not started

## Roadmap v2 Phase 3 Local Data Store and Migration Layer

Date: 2026-07-03

Scope:

- Add a local SQLite metadata catalogue while preserving existing JSON-backed
  runtime behavior.
- Keep generated vector payloads, uploaded files, chunks, extracted text, and
  repository index payloads in their existing artifact stores.
- Add forward-only metadata migrations and startup migration checks.
- Add a manual metadata migration/status command.
- Import existing JSON metadata where practical: users, local settings,
  backend conversations, document metadata, vector collection metadata, and
  repository index metadata.
- Mirror backend-persisted conversation writes into the metadata catalogue.
- Do not add background jobs, job APIs, progress events, vector production
  adapters, cloud sync, or multi-device sync.

### Storage Design

Phase 3 uses SQLite for metadata only:

```text
data/metadata/app.sqlite3
```

Initial tables:

- `schema_migrations`
- `users`
- `settings`
- `conversations`
- `documents`
- `vector_collections`
- `repository_indexes`

The existing JSON stores remain intact. The metadata database can be backed up
with `data/` or regenerated from JSON metadata artifacts by rerunning
migrations if the database file is missing.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Docker was available after running Docker Compose outside the restricted
  filesystem sandbox.
- The first Docker attempt inside the sandbox could not read
  `C:\Users\naran\.docker\config.json`; the approved outside-sandbox rerun
  succeeded.
- Frontend source behavior did not change in this phase. Local frontend tests
  were not rerun, but the Docker frontend test service ran lint, Vitest, and
  production build successfully.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_metadata_migrations.py tests\test_conversations.py` | Passed | 14 passed before docs/config follow-up. |
| `.venv\Scripts\python.exe -m pytest tests\test_repository_hygiene.py` | Passed | 2 passed. |
| `.venv\Scripts\python.exe -m pytest tests\test_metadata_migrations.py tests\test_conversations.py tests\test_repository_hygiene.py` | Passed | 17 passed after config guard update. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 119 passed, 7 skipped. Optional OCRmyPDF, live Ollama, and local Chroma tests skipped. |
| `$env:METADATA_DATABASE_FILE = "$env:TEMP\local-ai-metadata-cli-test.sqlite3"; Set-Location backend; ..\.venv\Scripts\python.exe -m app.metadata.cli migrate` | Passed | Initialized a temporary metadata database at schema version 1, then the temp file was removed. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Failed, then passed | Initial sandbox run could not read Docker config. Approved outside-sandbox rerun built both test images. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | 120 passed, 6 skipped in Docker. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test` | Passed | Frontend lint passed; 8 Vitest files and 50 tests passed; production build passed. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Removed the temporary Docker test network. |

### Phase 3 Verification Checklist

- [x] Fresh install metadata database initialization is tested
- [x] Existing JSON metadata migration is tested
- [x] Corrupt database handling is tested
- [x] Failed migration safety is tested
- [x] Conversation persistence regression and metadata mirroring are tested
- [x] Existing backend suite passes
- [x] Docker backend and frontend test services pass
- [x] Backup/restore and architecture docs include the metadata database
- [x] Generated metadata database files are ignored by Git
- [x] Phase 4 was not started

## Roadmap v2 Phase 4 Background Jobs and Runtime Progress

Date: 2026-07-03

Scope:

- Add a small local background job service for runtime progress.
- Persist job metadata in the Phase 3 SQLite metadata store.
- Add job status/list/cancel API endpoints.
- Add job-backed document processing and document indexing endpoints while
  preserving existing synchronous document endpoints.
- Add minimal frontend progress display for document processing/indexing.
- Keep cancellation conservative and local; no external queue, Redis, Celery,
  job API expansion beyond this phase, or vector backend work.

### Job Design

Jobs are executed in-process with `asyncio.create_task` and persisted to the
SQLite `jobs` table. Supported states are `queued`, `running`, `succeeded`,
`failed`, `cancel_requested`, and `cancelled`. Cancellation is best-effort and
checked only before or between safe steps; active Ollama requests are not
interrupted mid-call.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Frontend test runtime: bundled Node executable under
  `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`.
- Vitest required an outside-sandbox rerun because esbuild could not read the
  Vite/Vitest config path inside the restricted filesystem sandbox.
- Docker CLI was present, but the daemon was not running during Phase 4 final
  Docker verification.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_jobs.py tests\test_metadata_migrations.py tests\test_documents.py tests\test_vector_indexes.py` | Failed, then passed | Initial run had one stale schema-version assertion; rerun passed with 39 passed, 1 skipped. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 125 passed, 7 skipped. Optional OCRmyPDF, live Ollama, and local Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src\api.test.js src\components\__tests__\workspace-components.test.jsx src\__tests__\app.integration.test.jsx` from `frontend/` | Failed, then passed | Sandbox run failed on restricted config path access; approved outside-sandbox rerun passed with 3 files and 29 tests. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Passed | 8 files passed, 52 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Blocked | Docker daemon was not running: `open //./pipe/docker_engine: The system cannot find the file specified.` |

### Phase 4 Verification Checklist

- [x] Job service state transitions are tested
- [x] Job status API and cancellation behavior are tested
- [x] Document process/index job endpoints are tested
- [x] Existing synchronous document endpoints still pass regression tests
- [x] Existing backend suite passes
- [x] Frontend progress display is tested
- [x] Frontend lint, tests, and build pass
- [x] Docker blocker documented
- [x] Phase 5 was not started

## Roadmap v2 Phase 5 Document Ingestion v2

Date: 2026-07-03

Scope:

- Add file-type sniffing for supported document uploads.
- Expand document extraction to DOCX, HTML, CSV, and TSV while preserving
  existing text, Markdown, and PDF behavior.
- Add extraction diagnostics and duplicate document detection.
- Keep OCR expansion out of scope while adding OCR selection/skip regression
  coverage.
- Preserve synchronous document endpoints and Phase 4 job-backed document
  flows.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Frontend test runtime: bundled Node executable under
  `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe`.
- Vitest required outside-sandbox reruns because esbuild could not read the
  Vite/Vitest config path inside the restricted filesystem sandbox.
- Docker was available for this phase. One Docker frontend run used a stale
  pre-rebuild image and was rerun after rebuilding `frontend-test`.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_documents.py tests\test_jobs.py tests\test_vector_indexes.py` | Passed | 39 passed, 1 skipped. Optional OCRmyPDF smoke skipped because the binary is not installed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe scripts\lint-check.mjs` from `frontend/` | Passed | Frontend lint guard passed for 39 files. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run src\components\__tests__\workspace-components.test.jsx` from `frontend/` | Failed, then passed | Sandbox run failed on restricted config path access; approved outside-sandbox rerun passed with 1 file and 11 tests. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 131 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vitest\vitest.mjs run` from `frontend/` | Failed, then passed | One streaming integration assertion was flaky in the first full run; after removing a stale legacy `/chat` test override and rerunning sequentially, 8 files and 53 tests passed. |
| `C:\Users\naran\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe node_modules\vite\bin\vite.js build` from `frontend/` | Passed | Production build completed successfully. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Failed, then passed | Initial sandbox run could not read Docker config. Approved outside-sandbox rerun built both test images. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | 132 passed, 6 skipped in Docker. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test` | Failed, then passed | Initial rerun used a stale pre-rebuild image. Rebuilt `frontend-test`, then lint, 8 Vitest files/53 tests, and production build passed. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Removed the temporary Docker test network. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |

### Phase 5 Verification Checklist

- [x] File-type sniffing is tested for malformed and mismatched uploads
- [x] DOCX extraction is tested
- [x] HTML extraction is tested
- [x] CSV and TSV extraction are tested
- [x] PDF and text regression tests pass
- [x] Duplicate document detection is tested
- [x] OCR selection/skip behavior is tested without requiring optional OCR tools
- [x] Extraction diagnostics are recorded and tested
- [x] Existing synchronous and job-backed document flows pass regression tests
- [x] Existing backend suite passes
- [x] Frontend upload file picker behavior is tested
- [x] Frontend lint, tests, and build pass
- [x] Docker backend and frontend test services pass
- [x] Phase 6 was not started

## Roadmap v2 Phase 6 Vector Store Production Adapters

Date: 2026-07-03

Scope:

- Keep JSON as the default vector backend and safe fallback.
- Strengthen the vector store adapter contract with portable collection
  export/import operations.
- Add vector backend health and fallback diagnostics.
- Add collection export/import and JSON-to-adapter migration endpoints.
- Preserve document indexing, search, and RAG source metadata behavior.
- Defer Qdrant and LanceDB executable adapters because they add dependency or
  service cost; expose them as deferred/unavailable adapter health entries.

### Adapter Design

`VectorStoreManager` now reports configured backend, active backend, fallback
state, index directory, and per-backend health checks. `JsonVectorStore` and
`ChromaVectorStore` share a portable collection payload format:
`local-ai-vector-collection-v1`. Chroma remains optional and is only active
when `chromadb` is installed and `VECTOR_STORE_BACKEND=chroma` is configured.
Unavailable or deferred targets fall back to JSON and report `fallbackUsed`.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- `chromadb` is not installed in the local `.venv`, so optional Chroma
  integration coverage skipped as expected.
- Frontend checks were not run because Phase 6 did not change frontend files.
- Docker CLI was present, but Docker verification could not be completed:
  sandboxed Docker could not read `C:\Users\naran\.docker\config.json`, and
  the approved outside-sandbox rerun was rejected by the environment usage
  limit gate.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m compileall backend\app` | Passed | Backend source compiled successfully. |
| `.venv\Scripts\python.exe -m pytest tests\test_vector_store_adapters.py tests\test_vector_indexes.py tests\test_component_capabilities.py` | Passed | 28 passed, 1 skipped. Chroma contract skipped because `chromadb` is not installed. |
| `.venv\Scripts\python.exe -m pytest tests\test_vector_store_adapters.py tests\test_vector_indexes.py tests\test_component_capabilities.py tests\test_chat.py` | Passed | 58 passed, 1 skipped. Covered adapter contract, vector APIs, component health, and RAG/chat regressions. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 136 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `docker compose -f docker-compose.test.yml build backend-test` | Blocked | Sandboxed run failed on Docker config access; approved outside-sandbox rerun was rejected by the environment usage-limit gate. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |
| `rg -n "Phase 5 persists\|future backend such as `chroma`\|Qdrant, and LanceDB remain compatibility options\|not wired yet\|Current retrieval uses local embeddings and JSON vector search" README.md docs backend tests` | Passed | Remaining stale matches were limited to historical verification-log text. |

### Phase 6 Verification Checklist

- [x] JSON remains default and safe
- [x] Optional Chroma tests skip cleanly when `chromadb` is unavailable
- [x] Chroma adapter contract is strengthened with export/import methods
- [x] Qdrant and LanceDB are explicitly deferred with health metadata
- [x] Vector backend health endpoint is tested
- [x] Collection export/import endpoints are tested
- [x] JSON-to-adapter migration fallback is tested
- [x] Collection metadata remains consistent across the JSON backend
- [x] RAG/chat source metadata regressions pass
- [x] Existing backend suite passes
- [x] Documentation and changelog are updated
- [x] Docker blocker documented
- [x] Phase 7 was not started

## Roadmap v2 Phase 7 Retrieval Quality Evaluation

Date: 2026-07-03

Scope:

- Add a small non-sensitive retrieval evaluation corpus.
- Add expected source fixtures for deterministic retrieval checks.
- Add a fake-provider evaluation harness for recall, best rank, source
  accuracy, warning behavior, and source metadata shape.
- Add regression coverage for source numbering in prompts and response
  payloads.
- Keep live model quality evaluation opt-in only and out of default tests.
- Do not change retrieval algorithms, repository RAG, or frontend
  architecture.

### Eval Harness Design

`app.evaluation.retrieval` accepts an existing `DocumentRetrievalPipeline`,
resolved execution context, conversation id, and `RetrievalEvalCase` list. It
does not call Ollama by default. Tests seed a temporary JSON vector store from
`tests/fixtures/retrieval_eval/corpus.json` and compare against
`tests/fixtures/retrieval_eval/expectations.json`.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Docker backend image includes `chromadb`, while the local `.venv` does not.
  One Phase 6 fallback test was patched to explicitly monkeypatch Chroma
  unavailable so it remains valid in both environments.
- Frontend checks were not run because Phase 7 did not change frontend files.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_retrieval_eval.py tests\test_vector_indexes.py tests\test_chat.py` | Passed | 45 passed. Covered eval harness, vector search, and RAG/chat source regressions. |
| `.venv\Scripts\python.exe -m compileall backend\app tests\test_retrieval_eval.py` | Passed | Backend source and retrieval eval test compiled successfully. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 139 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `docker compose -f docker-compose.test.yml build backend-test` | Failed, then passed | Sandboxed run could not read Docker config; approved outside-sandbox build succeeded. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Failed, then passed | First Docker run exposed a cross-environment Chroma availability assumption; after patching and rebuilding, Docker backend passed with 140 passed, 6 skipped. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Removed the temporary Docker test network. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |

### Phase 7 Verification Checklist

- [x] Eval corpus is committed and non-sensitive
- [x] Expected retrieval/source fixtures are committed
- [x] Metrics are stable under fake providers
- [x] Recall, best rank, source accuracy, warning behavior, and metadata shape are tested
- [x] Prompt source numbering regression is tested
- [x] Live eval remains opt-in only
- [x] Targeted retrieval/RAG tests pass
- [x] Existing backend suite passes
- [x] Docker backend test service passes
- [x] Documentation and changelog are updated
- [x] Phase 8 was not started

## Roadmap v2 Phase 8 Unified Repository Intelligence

Date: 2026-07-04

Scope:

- Preserve legacy `/repos/index-local` and `/repos/ask` keyword repository RAG.
- Add repository file fingerprints and stale-index warnings.
- Add configured local repository root validation.
- Add opt-in repository vector indexing and vector search endpoints.
- Store repository vector collections separately from document vector
  collections.
- Do not add Git clone/update automation, language-aware parsing, Tree-sitter,
  or Phase 9 work.

### Repository Intelligence Design

Legacy repository indexes remain JSON files under `data/indexes/` and now
include file metadata plus a deterministic fingerprint. Repository vector
indexing reuses the existing settings resolver, embedder provider, and active
vector store, but writes `sourceType=repository` collections with `repo-*`
collection ids so document search and document RAG remain isolated.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Docker verification was run after approving Docker Compose access outside the
  workspace sandbox.
- Frontend checks were not run because Phase 8 did not change frontend files.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_repositories.py` | Passed | 5 passed. Covered legacy repo RAG, stale warnings, vector opt-in/search, document search isolation, and root validation. |
| `.venv\Scripts\python.exe -m pytest tests\test_vector_indexes.py tests\test_chat.py` | Passed | 42 passed. Nearby vector/document RAG regressions remained green. |
| `.venv\Scripts\python.exe -m pytest tests\test_repositories.py tests\test_vector_indexes.py tests\test_chat.py` | Passed | 47 passed after docs/config updates. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 144 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `.venv\Scripts\python.exe -m compileall backend\app tests\test_repositories.py` | Passed | Backend app and new repository tests compiled successfully. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |
| `docker compose -f docker-compose.test.yml build backend-test` | Failed, then passed | Sandboxed run could not read Docker config; approved outside-sandbox build succeeded. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | Docker backend passed with 145 passed, 6 skipped. Live Ollama skipped; repository metadata check skipped because `.git` is not available in the container context. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Removed the temporary Docker test network. |

### Phase 8 Verification Checklist

- [x] Legacy keyword repository RAG still works
- [x] Vector repository indexing is opt-in
- [x] Repository paths stay inside configured allowed roots
- [x] Freshness warnings are clear and tested
- [x] Repository vector collections do not leak into document search/RAG
- [x] Targeted repo/vector/chat tests pass
- [x] Existing backend suite passes
- [x] Docker backend test service passes
- [x] Documentation and changelog are updated
- [x] Phase 9 was not started

## Roadmap v2 Phase 9 Language-Aware Code Parsing

Date: 2026-07-04

Scope:

- Add lightweight language-aware repository chunking without heavy parser
  dependencies.
- Preserve existing repository index readability by keeping legacy chunk fields
  and treating metadata as optional.
- Add symbol metadata for practical Python, JS/TS, Markdown, JSON/YAML, HTML,
  and CSS fixtures.
- Fall back to line-based chunks when parsing fails or no symbols are found.
- Surface symbol context in repository prompt citations and repository vector
  search metadata.
- Do not start Phase 10 frontend architecture work.

### Parser Design

Python uses the standard-library `ast` module for top-level classes and
functions. JS/TS, Markdown, YAML, HTML, and CSS use conservative regex
heuristics. JSON uses the standard-library `json` module for top-level object
keys. All parser paths fall back to existing line-aware chunking, and repository
chunks still include `content`, `file_path`, `start_line`, and `end_line`.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- No frontend files changed, so frontend lint/tests/build were not run.
- Docker verification was run after approving Docker Compose access outside the
  workspace sandbox.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest tests\test_repository_parsing.py tests\test_repositories.py` | Failed, then passed | First run exposed an indexer indentation typo and a Markdown heading metadata bug; after fixes, 10 passed. |
| `.venv\Scripts\python.exe -m pytest tests\test_repository_parsing.py tests\test_repositories.py tests\test_vector_indexes.py tests\test_chat.py` | Passed | 52 passed. Covered parser fixtures, repo API, vector search, and chat regressions. |
| `.venv\Scripts\python.exe -m pytest` | Passed | 149 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `.venv\Scripts\python.exe -m compileall backend\app tests\test_repository_parsing.py tests\test_repositories.py` | Passed | Backend app and repository parser/API tests compiled successfully. |
| `.venv\Scripts\python.exe -m pip check` | Passed | No broken requirements found. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |
| `docker compose -f docker-compose.test.yml build backend-test` | Failed, then passed | Sandboxed run could not read Docker config; approved outside-sandbox build succeeded. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | Docker backend passed with 150 passed, 6 skipped. Live Ollama skipped; repository metadata check skipped because `.git` is not available in the container context. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Removed the temporary Docker test network. |

### Phase 9 Verification Checklist

- [x] Parser failures fall back safely
- [x] Line ranges remain accurate in parser fixtures
- [x] Existing version-1 repository indexes remain retrievable
- [x] Source citations show useful symbol context
- [x] Repository vector search returns language and symbol metadata
- [x] Targeted parser/repo/vector/chat tests pass
- [x] Existing backend suite passes
- [x] Docker backend test service passes
- [x] Documentation and changelog are updated
- [x] Phase 10 was not started

## Roadmap v2 Phase 10 Frontend State and Component Architecture

Date: 2026-07-04

Scope:

- Extract chat send/stream logic from `App.jsx` into `useChatSender`.
- Extract document upload/process/index/search workflow state into
  `useDocumentWorkflow`.
- Extract API key localStorage ownership into `useStoredApiKey`.
- Keep visual components and UI behavior unchanged.
- Preserve browser-local conversation fallback, backend migration behavior,
  document ingestion/job progress, RAG indicators, and settings flows.
- Do not start Phase 11 accessibility/mobile/UX polish work.

### Frontend State Boundaries

`App.jsx` remains the application shell for authentication restoration, chat
list lifecycle, conversation persistence mode, navigation/dialog state, and
toasts. Workflow hooks now own focused state:

- `useChatSender`: optimistic user/assistant message creation, SSE token
  updates, response metadata mapping, and send errors.
- `useDocumentWorkflow`: document cache, index cache, upload/process/index job
  polling, retrieval-only search, warnings, and document errors.
- `useStoredApiKey`: API key localStorage read/write boundary.

### Environment Notes

- Host shell: Windows PowerShell.
- Frontend local `npm` was not available on PATH, so commands used the bundled
  Node runtime path and local project binaries.
- Initial sandboxed Vitest run could not load the config because esbuild tried
  to read restricted paths; the approved outside-sandbox run succeeded.
- Backend files were not changed during Phase 10, so backend tests were not
  rerun for this phase.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `npm run test:run -- src/hooks/useStoredApiKey.test.js src/hooks/useChatSender.test.js src/hooks/useDocumentWorkflow.test.js src/__tests__/app.integration.test.jsx` from `frontend/` | Blocked | Global `npm` was not available in this shell. |
| `.\\node_modules\\.bin\\vitest.cmd run src/hooks/useStoredApiKey.test.js src/hooks/useChatSender.test.js src/hooks/useDocumentWorkflow.test.js src/__tests__/app.integration.test.jsx` from `frontend/` with bundled Node on PATH | Failed, then passed | Sandboxed run could not load Vitest config; approved run passed with 4 files and 17 tests. |
| `node scripts\lint-check.mjs` from `frontend/` with bundled Node on PATH | Passed | Lint guard passed for 45 frontend files. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `frontend/` with bundled Node on PATH | Passed | 11 files and 62 tests passed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` with bundled Node on PATH | Passed | Production build succeeded. |
| `docker compose -f docker-compose.test.yml build frontend-test` | Failed, then passed | Sandboxed run could not read Docker config; approved outside-sandbox build succeeded. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test` | Passed | Docker frontend lint, Vitest, and production build passed; 62 Vitest tests passed. React act warnings appeared in existing accessibility tests but did not fail the suite. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Removed the temporary Docker test network. |

### Phase 10 Verification Checklist

- [x] No UI redesign was introduced
- [x] Chat send/stream behavior is covered by focused hook tests
- [x] Document workflow behavior is covered by focused hook tests
- [x] API key storage boundary is covered by focused hook tests
- [x] Existing app integration tests pass
- [x] Conversation localStorage/backend migration behavior remains covered
- [x] Frontend lint, full Vitest, and production build pass
- [x] Docker frontend test service passes
- [x] Documentation and changelog are updated
- [x] Phase 11 was not started

## Roadmap v2 Phase 11 Accessibility, Mobile, and UX Polish

Date: 2026-07-04

Scope:

- Improve keyboard and screen-reader affordances for composer status, document
  job progress, document search warnings/errors, source citations, settings
  drawer focus, shared modal focus, and assistant streaming/warning states.
- Improve narrow-screen wrapping for composer document chips, document search
  controls/results, and source citation chips.
- Preserve existing chat, RAG, repository, document, settings, persistence, and
  job behavior.
- Do not start Phase 12 security hardening work.

### Frontend Accessibility and Mobile Notes

The composer now exposes a polite status region for sending, document
processing, document search, and warning states. Document jobs expose progress
semantics. Source citations are grouped as a list while preserving each source
as a button. The settings drawer focuses its close control when opened, and the
shared modal primitive focuses the first actionable control. Mobile CSS wraps
long document and source text rather than clipping or overflowing it.

### Environment Notes

- Host shell: Windows PowerShell.
- Frontend local `npm` was not used; commands used the bundled Node runtime
  path and local project binaries.
- Initial sandboxed Vitest run could not load the Vite/Vitest config because
  esbuild tried to read a restricted parent directory; approved outside-sandbox
  reruns succeeded.
- Backend files were not changed during Phase 11, so backend tests were not
  rerun for this phase.
- Docker was available and the frontend test service passed.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.\\node_modules\\.bin\\vitest.cmd run src\\components\\__tests__\\workspace-components.test.jsx src\\__tests__\\accessibility.a11y.test.jsx` from `frontend/` with bundled Node on PATH | Failed, then passed | Sandboxed run could not load the config. First approved run exposed a missing progressbar implementation on document job progress; after the fix, 2 files and 15 tests passed. |
| `node scripts\\lint-check.mjs` from `frontend/` with bundled Node on PATH | Passed | Lint guard passed for 45 frontend files. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `frontend/` with bundled Node on PATH | Passed | 11 files and 63 tests passed. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` with bundled Node on PATH | Passed | Production build succeeded. |
| `docker compose -f docker-compose.test.yml build frontend-test` | Passed | Rebuilt the frontend test image. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test` | Passed | Docker frontend lint, Vitest, and production build passed; 11 Vitest files and 63 tests passed. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Removed the temporary Docker test network. |

### Phase 11 Verification Checklist

- [x] Keyboard focus improvements are covered for shared modals and settings
      drawer opening.
- [x] Composer/document progress status semantics are covered by component
      tests.
- [x] Source citation list/button semantics are covered by component tests.
- [x] Existing axe accessibility smoke coverage passes.
- [x] Frontend lint, full Vitest, and production build pass.
- [x] Docker frontend test service passes.
- [x] Documentation and changelog are updated.
- [x] Phase 12 was not started.

## Roadmap v2 Phase 12 Security Hardening v2

Date: 2026-07-04

Scope:

- Add CSRF protection for unsafe session-cookie routes.
- Add optional signed session cookies through `SESSION_SIGNING_KEY`.
- Add in-memory login rate limiting and lockout behavior.
- Add backend security response headers.
- Add redacted audit logging for auth and API-key changes.
- Add API-key rotation UX in Settings while preserving explicit save behavior.
- Preserve local development defaults and trusted-network limitations.
- Do not start Phase 13 diagnostics/observability work.

### Security Design Notes

Session routes still use the local credentials file and browser cookies. By
default, sessions remain in-memory for simple local development. When
`SESSION_SIGNING_KEY` is configured, session cookies are HMAC-signed and can be
validated after backend restart until they expire. Unsafe cookie-authenticated
requests require the readable CSRF cookie to match the `X-CSRF-Token` header.
Bearer-key AI/data routes remain bearer-protected and do not use the browser
session cookie.

Login rate limiting is in-memory by username and client address. Audit logs are
written through `app.audit` and include event, username, client, success state,
and reason where useful; passwords and API-key values are not logged.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Frontend local `npm` was not used; commands used the bundled Node runtime
  path and local project binaries.
- Sandboxed Vitest could not load Vite/Vitest config because esbuild tried to
  read a restricted parent directory. An escalation request to rerun Vitest was
  rejected by the environment usage-limit guard, so frontend Vitest was not
  completed in this phase.
- Docker Compose could not read `C:\Users\naran\.docker\config.json` inside the
  sandbox. Escalation was not available due the same usage-limit guard, so
  Docker verification was blocked.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_login.py tests\\test_account.py tests\\test_browser_session_flow.py tests\\test_auth.py` | Passed | 13 passed. Covered login cookies, CSRF, rate limiting, signed sessions, security headers, and audit redaction. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Final run passed with 155 passed and 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `.\\node_modules\\.bin\\vitest.cmd run src\\api.test.js src\\components\\AccountPanel.conversation-settings.test.jsx` from `frontend/` with bundled Node on PATH | Blocked | Sandboxed run failed to load config due restricted parent-directory access. Escalated rerun was rejected by the environment usage-limit guard. |
| `node scripts\\lint-check.mjs` from `frontend/` with bundled Node on PATH | Passed | Lint guard passed for 45 frontend files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` with bundled Node on PATH | Passed | Production build succeeded. |
| `.venv\\Scripts\\python.exe -m compileall backend\\app\\auth backend\\app\\routers tests\\test_login.py tests\\test_account.py` | Passed | Auth/session/router code and targeted tests compiled successfully. |
| `.venv\\Scripts\\python.exe -m compileall backend\\app tests\\test_login.py tests\\test_account.py` | Passed | Backend app and targeted security tests compiled successfully. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Blocked | Docker config access was denied in the sandbox: `C:\Users\naran\.docker\config.json: Access is denied.` Escalation was unavailable due the usage-limit guard. |

### Phase 12 Verification Checklist

- [x] Auth routes remain usable locally.
- [x] Unsafe session-cookie routes require CSRF tokens.
- [x] Optional signed sessions are covered by regression tests.
- [x] Login rate limiting is covered by regression tests.
- [x] Security headers are covered by regression tests.
- [x] Audit logs avoid passwords and API-key values.
- [x] Backend targeted and full test suites pass.
- [x] Frontend lint and production build pass.
- [x] Security controls and limitations are documented.
- [x] Phase 13 was not started.

## Roadmap v2 Phase 13 Observability and Diagnostics

Date: 2026-07-04

Scope:

- Add safe structured diagnostics endpoints for runtime, model, document,
  retrieval/vector, and job status.
- Add a metadata-only support-bundle endpoint.
- Add recursive redaction helpers for secrets, session/cookie/CSRF values,
  prompts, chat text, document/OCR contents, and private paths.
- Add a small frontend Diagnostics panel reachable from the existing rail.
- Do not start Phase 14 packaging/deployment-template work.

### Diagnostics Design

`GET /diagnostics/status` and `GET /diagnostics/support-bundle` are
Bearer-protected. The status payload reports counts, modes, backend health, and
recent job state only. The support bundle wraps the same diagnostics with
redaction metadata. Redaction runs recursively over the returned payload and is
covered by tests with intentionally sensitive fixture data.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- Frontend commands used the bundled Node runtime path and local project
  binaries.
- Targeted Vitest was blocked by the same sandbox config-read limitation seen
  in Phase 12; this blocker was recorded once.
- Docker Compose was blocked by sandboxed access to
  `C:\Users\naran\.docker\config.json`; this blocker was recorded once.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_diagnostics.py tests\\test_health.py tests\\test_jobs.py tests\\test_models.py` | Failed, then passed | Initial runs tightened support-bundle redaction for declaration fields and neutral field names; final run passed with 15 passed. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed with 159 passed and 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `node scripts\\lint-check.mjs` from `frontend/` with bundled Node on PATH | Passed | Lint guard passed for 46 frontend files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` with bundled Node on PATH | Passed | Production build succeeded. |
| `.\\node_modules\\.bin\\vitest.cmd run src\\__tests__\\app.integration.test.jsx src\\api.test.js` from `frontend/` with bundled Node on PATH | Blocked | Sandboxed run failed to load config due restricted parent-directory access. |
| `docker compose -f docker-compose.test.yml build backend-test frontend-test` | Blocked | Docker config access was denied in the sandbox: `C:\Users\naran\.docker\config.json: Access is denied.` |
| `.venv\\Scripts\\python.exe -m compileall backend\\app\\services\\diagnostics.py backend\\app\\services\\redaction.py backend\\app\\routers\\diagnostics.py tests\\test_diagnostics.py` | Passed | New diagnostics service/router/tests compiled successfully. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |

### Phase 13 Verification Checklist

- [x] Diagnostics endpoints require Bearer API key.
- [x] Support bundle is metadata-only by default.
- [x] Redaction strips secrets, tokens, cookies, sessions, CSRF values, prompt
      and chat content, document/OCR content, and private paths.
- [x] Runtime/model/document/retrieval/job summaries are structured and bounded.
- [x] Frontend diagnostics panel builds successfully.
- [x] Backend targeted and full test suites pass.
- [x] Documentation and changelog are updated.
- [x] Phase 14 was not started.

## Roadmap v2 Phase 14 Packaging and Deployment Templates

Date: 2026-07-04

Scope:

- Add a production-style Compose template with safe defaults.
- Add local deployment environment validation tooling.
- Add an upgrade helper that validates and backs up `data/` before container
  replacement.
- Update setup, deployment, backup, release, README, and changelog docs.
- Do not start Phase 15 public release candidate QA.

### Packaging Design

`docker-compose.prod.yml` keeps the backend on host networking for local
Ollama access, binds the frontend to `127.0.0.1:${FRONTEND_PORT:-5173}` by
default, mounts `./data` as the only mutable application state, and mounts
repositories read-only at `/repositories`. It does not publish Ollama or map a
public backend API port.

`scripts/validate_env.py` checks local production readiness without external
dependencies. `scripts/upgrade.py` runs validation, creates
`backups/pre-upgrade-data-*.zip` from `data/`, and only runs Docker Compose
when `--apply` is passed.

Systemd examples were deferred because they would be host-specific and larger
than the smallest safe Phase 14 slice.

### Environment Notes

- Host shell: Windows PowerShell.
- Backend test runtime: Python 3.12.13 from `.venv`.
- The local checkout intentionally lacks production secrets (`.env`,
  `backend/.env`, and `data/config/credentials.json`), so env validation fails
  with actionable setup errors in this environment.
- Docker Compose config validation was blocked by sandboxed access to
  `C:\Users\naran\.docker\config.json`.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_deployment_scripts.py` | Passed | 4 passed. Covered env validation and backup archive creation. |
| `.venv\\Scripts\\python.exe -m compileall scripts\\validate_env.py scripts\\upgrade.py tests\\test_deployment_scripts.py` | Passed | Scripts and tests compiled successfully. |
| `.venv\\Scripts\\python.exe scripts\\validate_env.py` | Failed as expected | Reported missing local production `.env`, `backend/.env`, and credentials, plus warnings for empty API/session values. This checkout does not contain secrets. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed with 163 passed and 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `docker compose -f docker-compose.prod.yml config` | Blocked | Docker config access was denied in the sandbox: `C:\Users\naran\.docker\config.json: Access is denied.` |

### Phase 14 Verification Checklist

- [x] Production Compose template does not expose Ollama by default.
- [x] Production Compose template keeps frontend localhost-bound by default.
- [x] Env validation reports unsafe or missing deployment configuration clearly.
- [x] Upgrade helper creates a data backup before Compose replacement.
- [x] Script tests pass.
- [x] Full backend suite passes.
- [x] Documentation and changelog are updated.
- [x] Phase 15 was not started.

## Roadmap v2 Phase 15 Public Release Candidate QA

Date: 2026-07-04

Scope:

- Freeze scope after Roadmap v2 Phase 14.
- Audit README, API, setup, backup/restore, deployment hardening, security,
  changelog, and release checklist docs for current release-candidate claims.
- Draft release notes for `0.2.0-rc1`.
- Run available backend, frontend lint/build, script, compile, hygiene, and
  docs-adjacent checks.
- Do not create a release tag unless all critical checks pass.
- Do not start Phase 16 or new roadmap work.

### Release Readiness Notes

The RC is not ready to tag from this environment. Backend tests, frontend lint,
frontend production build, script tests, compile checks, and whitespace checks
passed. Frontend Vitest and Docker/Compose validation were blocked by sandbox
access restrictions. Production env validation correctly failed because this
checkout does not include local secrets or credentials.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_deployment_scripts.py tests\\test_diagnostics.py tests\\test_login.py tests\\test_account.py` | Passed | 17 passed. Covered deployment scripts, diagnostics, login, and account security tests. |
| `.venv\\Scripts\\python.exe -m compileall backend\\app scripts tests\\test_deployment_scripts.py tests\\test_diagnostics.py` | Passed | Backend app, scripts, and targeted tests compiled successfully. |
| `git ls-files -ci --exclude-standard` | Passed | No tracked ignored files were reported. |
| `rg -n "coming soon\|not implemented\|future upload\|backend does not persist\|Conversations live in browser localStorage\|external vector database backends are not wired\|not wired yet\|TODO\|FIXME" README.md docs CHANGELOG.md SECURITY.md` | Passed | Remaining matches are accurate limitations or historical verification-log/roadmap text. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed with 163 passed and 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `node scripts\\lint-check.mjs` from `frontend/` with bundled Node on PATH | Passed | Lint guard passed for 46 frontend files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` with bundled Node on PATH | Passed | Production build succeeded. |
| `.venv\\Scripts\\python.exe scripts\\validate_env.py` | Failed as expected | Reported missing local production `.env`, `backend/.env`, and credentials, plus warnings for empty API/session values. This checkout does not contain secrets. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `frontend/` with bundled Node on PATH | Blocked | Sandboxed run failed to load config due restricted parent-directory access. |
| `docker compose -f docker-compose.prod.yml config` | Blocked | Docker config access was denied in the sandbox: `C:\Users\naran\.docker\config.json: Access is denied.` |
| `Test-Path docs\\assets\\login-preview.png; Test-Path docs\\assets\\dashboard-preview.png` | Passed | Both screenshot assets exist. |
| `git tag --list` | Passed | No existing local tags were listed; no tag was created. |

### Phase 15 Verification Checklist

- [x] Scope frozen for Phase 15.
- [x] README/docs/API/security/setup/backup/deployment docs audited.
- [x] Changelog updated with RC status.
- [x] Release notes drafted.
- [x] Backend full test suite passed.
- [x] Frontend lint and production build passed.
- [x] Script/config tests passed.
- [x] `git diff --check` passed.
- [x] Screenshot references exist.
- [x] Release blockers and deferred checks documented.
- [x] No release tag was created.
- [x] Phase 16/new roadmap work was not started.

## Roadmap v2 Phase 16 Stable v2 Release and Post-RC Stabilization

Date: 2026-07-05

Scope:

- Review Phase 15 verification, release checklist, changelog, README, setup,
  deployment hardening, security, and backup docs.
- Prepare stable v2 release notes without adding new feature work.
- Add support and hotfix guidance.
- Re-run release verification available in this environment.
- Do not start Phase 17 or new feature work.

### Release Status

Stable v2 is not tagged from this environment. The remaining blockers are
environmental or manual release gates: frontend Vitest in a non-sandboxed
frontend environment, Docker/Compose validation with readable Docker config,
target-machine production env validation, manual browser smoke, and optional
live Ollama smoke.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_deployment_scripts.py tests\\test_diagnostics.py tests\\test_login.py tests\\test_account.py` | Passed | 17 passed. Covered deployment scripts, diagnostics, login, and account/security behavior. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed with 163 passed and 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma tests skipped. |
| `node scripts\\lint-check.mjs` from `frontend/` with bundled Node on PATH | Passed | Lint guard passed for 46 frontend files. |
| `.\\node_modules\\.bin\\vite.cmd build` from `frontend/` with bundled Node on PATH | Passed | Production build succeeded. |
| `.venv\\Scripts\\python.exe scripts\\validate_env.py` | Failed as expected | Reported missing local production `.env`, `backend/.env`, and credentials, plus warnings for empty API/session values. This checkout does not contain secrets. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF warnings on Windows. |
| `git tag --list` | Passed | No existing local tags were listed; no tag was created. |
| `docker compose -f docker-compose.prod.yml config` | Blocked | Docker config access was denied in the sandbox: `C:\Users\naran\.docker\config.json: Access is denied.` |

### Phase 16 Verification Checklist

- [x] Phase 15 verification log and release checklist reviewed.
- [x] README, setup, deployment hardening, security, and backup docs reviewed.
- [x] Stable v2 release notes prepared.
- [x] Support and hotfix guidance added.
- [x] Backend full test suite passed.
- [x] Frontend lint and production build passed.
- [x] Deployment script tests passed.
- [x] `git diff --check` passed.
- [x] Remaining release blockers documented.
- [x] No release tag was created.
- [x] Phase 17/new feature work was not started.

## Proposed Frontend Migration Phase 24 End-to-End Release Verification

Date: 2026-07-25

Scope:

- Verify the promoted `proposedFrontend/` locally and in Docker.
- Re-run backend, frontend, e2e, Compose, image build, Docker test, and optional
  live Ollama smoke checks where available.
- Do not start Phase 25 public-release polish.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed: 185 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma checks skipped. |
| `.\\node_modules\\.bin\\oxfmt.cmd --check .` from `proposedFrontend/` | Failed, then passed | Initial formatting drift was corrected. Formatter-sensitive inline object test types were replaced with interfaces so final formatting, ESLint, and TypeScript checks all pass. |
| `.\\node_modules\\.bin\\eslint.cmd .` from `proposedFrontend/` | Passed | Proposed frontend ESLint completed successfully. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Proposed frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Passed | Full proposed frontend suite passed: 21 files, 100 tests. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Proposed frontend production build succeeded. |
| `.\\node_modules\\.bin\\playwright.cmd test --config playwright.config.ts` from `proposedFrontend/` | Passed | Chromium e2e suite passed: 6 tests. |
| `docker compose config` | Passed | Default Compose config resolved. |
| `docker compose -f docker-compose.prod.yml config` | Passed | Production Compose config resolved. |
| `docker compose -f docker-compose.test.yml config` | Passed | Test Compose config resolved. |
| `docker compose build frontend` | Passed | Promoted frontend Docker image built successfully. |
| `docker compose -f docker-compose.test.yml build frontend-test` | Passed | Frontend test image built successfully. |
| `docker compose -f docker-compose.test.yml run --rm backend-test` | Passed | Dockerized backend suite passed: 150 passed, 6 skipped. |
| `docker compose -f docker-compose.test.yml run --rm frontend-test sh -c "pnpm lint --quiet && pnpm typecheck && pnpm exec vitest run --reporter=dot && pnpm build"` | Failed, then passed | Initial run exposed a Docker-only timeout in a long repository workflow test. After raising that test timeout to 15 seconds, the command passed with 21 files, 100 tests, plus production build. |
| `.venv\\Scripts\\python.exe -m pytest tests\\test_ollama_smoke.py tests\\test_live_ollama.py -m ollama` | Passed with skips | Five optional live Ollama tests skipped cleanly because `RUN_OLLAMA_TESTS=1` was not set. |
| `docker compose -f docker-compose.test.yml down --remove-orphans` | Passed | Temporary Docker test network was removed. |

### Phase 24 Verification Checklist

- [x] Backend full pytest passed.
- [x] Proposed frontend format, lint, typecheck, tests, and build passed.
- [x] Proposed frontend Playwright e2e passed.
- [x] Compose config validation passed for default, production, and test files.
- [x] Promoted frontend Docker images built.
- [x] Dockerized backend and frontend test suites passed.
- [x] Optional live Ollama smoke remains opt-in and skips cleanly by default.
- [x] Phase 25 public-release polish was not started.

## Proposed Frontend Migration Phase 25 Public Release Polish

Date: 2026-07-25

Scope:

- Refresh release-facing documentation after the promoted frontend migration.
- Update stale checklist/changelog entries from pending verification to
  completed verification where Phase 24 proved them.
- Add manual local smoke commands for running the promoted frontend.
- Finish the 25-phase migration track without adding new product features.

### Commands Attempted

| Command | Result | Notes |
| --- | --- | --- |
| `rg -n "frontend/|proposedFrontend|legacy frontend|old frontend|not implemented|coming soon|future" README.md docs CHANGELOG.md mitigationPlan.md` | Passed | Used to identify stale public-release wording. Remaining matches are historical migration records, accurate limitations, or intentional references to the archived legacy frontend. |
| Documentation review | Passed | README, changelog, release checklist, backup/restore, dependency review, setup, testing, and deployment hardening docs were reviewed and updated where needed. |
| `.venv\\Scripts\\python.exe -m pytest` | Passed | Full backend suite passed: 185 passed, 7 skipped. Optional OCRmyPDF, live Ollama, Ollama smoke, and local Chroma checks skipped. |
| `.\\node_modules\\.bin\\oxfmt.cmd --check .` from `proposedFrontend/` | Passed | Promoted frontend format check passed. |
| `.\\node_modules\\.bin\\eslint.cmd .` from `proposedFrontend/` | Passed | Promoted frontend ESLint completed successfully. |
| `.\\node_modules\\.bin\\tsc.cmd --noEmit` from `proposedFrontend/` | Passed | Promoted frontend TypeScript check completed successfully. |
| `.\\node_modules\\.bin\\vite.cmd build` from `proposedFrontend/` | Passed | Promoted frontend production build succeeded. |
| `.\\node_modules\\.bin\\vitest.cmd run` from `proposedFrontend/` | Failed, then passed | First run hit the command timeout while jsdom was slow and showed profile tests mid-failure. Focused profile rerun passed: 6 tests. Full suite rerun with a longer timeout passed: 21 files, 100 tests. |
| `git diff --check` | Passed | No whitespace errors; Git reported expected LF-to-CRLF working-copy warnings on Windows. |

### Phase 25 Verification Checklist

- [x] README public-release copy reviewed and updated.
- [x] Changelog reflects completed promoted-frontend verification.
- [x] Release checklist points at promoted frontend commands.
- [x] Backup/restore docs include `proposedFrontend/.env`, `node_modules`, and
  `dist` paths.
- [x] Dependency-review docs include `proposedFrontend` pnpm and Docker files.
- [x] Manual local smoke commands documented.
- [x] Backend and promoted frontend local verification passed after docs
  updates.
- [x] `git diff --check` passed.
- [x] No new feature work was started.
- [x] The 25-phase proposed frontend migration plan is complete.
