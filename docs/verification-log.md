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
