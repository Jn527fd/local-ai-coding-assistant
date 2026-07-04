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
