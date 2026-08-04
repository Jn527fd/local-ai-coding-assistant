# Development Roadmap

This roadmap is the working 15-phase plan for hardening and scaling Local AI
Coding Assistant.

The original roadmap was created in conversation before it was checked into
the repository. This file records the plan as the project artifact going
forward, aligned with the completed and approved Phase 1 through Phase 4 work
and the in-progress Phase 5 repository hygiene work.

No phase should begin until the previous phase has been implemented, tested,
reviewed, and verified.

## Phase 1: Baseline Stabilization

### Objective

Establish a trustworthy baseline for the current branch before changing
behavior.

### Why This Phase Matters

The project already has backend, frontend, Docker, RAG, reranking, and
compression behavior. Future work needs a known-good test and build baseline
so regressions are visible.

### Implementation Tasks

- Inspect current test, build, Docker, and dependency workflows.
- Run local checks where possible and Docker checks where local tools are
  missing.
- Record all blockers and verification commands in a persistent log.
- Fix only narrow issues required to make the existing suite reliable.

### Testing Requirements

- Run backend tests.
- Run frontend lint, tests, and production build.
- Run Dockerized backend and frontend tests when Docker is available.
- Add or update regression tests only for baseline failures discovered in this
  phase.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass, if available
- [x] Documentation updated, if applicable
- [x] No new critical or high-severity issues introduced
- [x] Baseline verification results are recorded

### Deliverables

- Verification log.
- Baseline test/build status.
- Minimal fixes for any baseline test instability.

### Risks or Blockers

- Local Python or Node may be missing.
- Docker may require environment files or daemon access.
- Existing generated artifacts may pollute results.

## Phase 2: Documentation and API Contract Alignment

### Objective

Align README, setup, architecture, testing, and API documentation with the
actual implemented application.

### Why This Phase Matters

The app evolved through several AI-platform phases. Documentation must match
real behavior before new work can be scoped safely.

### Implementation Tasks

- Review routers, schemas, services, frontend API helpers, tests, and docs.
- Update API documentation for implemented endpoints and auth requirements.
- Document per-chat settings, component discovery, documents, RAG, reranking,
  compression, and known fallback/discovery-only areas.
- Avoid adding new runtime behavior.

### Testing Requirements

- Run backend tests.
- Run frontend lint, tests, and production build.
- Run docs-related search checks for stale claims.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass, if available
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Docs distinguish implemented, fallback, discovery-only, and planned
  features

### Deliverables

- Updated README.
- Updated API documentation.
- Updated architecture, setup, and testing documentation.
- Verification log entries.

### Risks or Blockers

- Some behavior may be ambiguous without deeper code inspection.
- Documentation-only changes can still become misleading if not verified
  against code.

## Phase 3: Capability Metadata Contract

### Objective

Enrich `/components/capabilities` with explicit, frontend-consumable execution
metadata.

### Why This Phase Matters

The settings UI exposes implemented capabilities, fallback modes, placeholders,
and discovery-only tools. The backend should describe those states directly so
the frontend does not infer them from names.

### Implementation Tasks

- Add additive metadata fields to each capability item.
- Preserve all existing capability categories, IDs, and `available` semantics.
- Mark implemented, fallback, placeholder, discovery-only, and unavailable
  capabilities clearly.
- Keep `/models/status` and existing selection behavior unchanged.

### Testing Requirements

- Add backend tests for capability metadata shape and status values.
- Verify known model categorization still works.
- Verify Ollama-unavailable behavior remains safe.
- Run full backend and frontend tests.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass, if available
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Capability metadata is additive and preserves existing IDs/categories

### Deliverables

- Updated component registry metadata contract.
- Backend tests for metadata.
- API and architecture documentation updates.

### Risks or Blockers

- Marking a fallback as implemented could mislead users.
- Changing IDs or `available` semantics could break settings resolution.

## Phase 4: Frontend Capability Metadata Display

### Objective

Display capability execution metadata in the existing per-chat Conversation
Settings UI.

### Why This Phase Matters

Users need to know whether a selected setting is fully implemented,
fallback-backed, discovery-only, planned, or unavailable without a UI redesign.

### Implementation Tasks

- Add read-only status text beneath selected capability controls.
- Keep the UI backward-compatible with older capability entries that lack
  metadata.
- Update frontend mocks to reflect the current capabilities contract.
- Avoid changing settings persistence or backend execution behavior.

### Testing Requirements

- Add frontend tests for visible capability metadata.
- Run accessibility tests.
- Run frontend lint, full tests, and production build.
- Run backend tests to confirm no contract regressions.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [x] Code builds successfully
- [x] Existing tests pass
- [x] New tests for this phase pass
- [x] Linting/static checks pass, if available
- [x] Documentation updated
- [x] No new critical or high-severity issues introduced
- [x] Capability metadata display is read-only and preserves settings behavior

### Deliverables

- Updated Account panel metadata display.
- Updated frontend mocks.
- Frontend regression tests.
- Documentation updates.

### Risks or Blockers

- Extra metadata text could clutter the settings drawer.
- Tests may need to handle text split across markup.

## Phase 5: Repository Hygiene Guard

### Objective

Remove tracked local artifacts and prevent ignored files from being committed
again.

### Why This Phase Matters

The repository had a tracked `.venv` even though `.gitignore` excludes virtual
environments. This creates noisy diffs, machine-specific paths, unnecessary
repository size, and cross-platform confusion.

### Implementation Tasks

- Identify tracked files that match `.gitignore`.
- Remove tracked ignored artifacts from the git index while keeping local
  files on disk.
- Add an automated repository hygiene test.
- Document the guard and verification commands.

### Testing Requirements

- Add a backend test that fails if tracked files match `.gitignore`.
- Verify the local virtual environment still runs after index cleanup.
- Run full backend tests.
- Run frontend lint, tests, and production build.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] No tracked files match `.gitignore`

### Deliverables

- `.venv` removed from version control.
- Repository hygiene regression test.
- Updated testing documentation.
- Verification log entry.

### Risks or Blockers

- `git rm --cached` must not delete the user's local virtual environment.
- The hygiene test depends on Git metadata and should skip cleanly if metadata
  is unavailable.

## Phase 6: CI and Repeatable Verification

### Objective

Move the verified local checks into repeatable CI workflows.

### Why This Phase Matters

The project now has enough backend, frontend, Docker, and hygiene coverage to
benefit from automatic checks on every branch and pull request.

### Implementation Tasks

- Add GitHub Actions for backend tests.
- Add GitHub Actions for frontend lint, tests, and build.
- Add optional Docker build/test jobs if runner time permits.
- Cache Python and npm dependencies safely.
- Ensure live Ollama tests remain opt-in and skipped by default.

### Testing Requirements

- Validate workflow syntax.
- Run equivalent local commands before committing CI changes.
- Confirm CI does not require Ollama, GPU, pulled models, or local secrets.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] CI passes on a clean branch

### Deliverables

- CI workflow files.
- Updated testing documentation.
- Verification notes for CI behavior.

### Risks or Blockers

- Docker jobs may be slow or unavailable on some runners.
- Windows and Linux path differences can expose hidden assumptions.

## Phase 7: Frontend State Decomposition

### Objective

Reduce `App.jsx` complexity by extracting focused hooks and state modules.

### Why This Phase Matters

`App.jsx` owns authentication, capabilities, conversations, documents,
indexes, chat sending, toasts, and dialogs. This works, but makes future UI
changes risky.

### Implementation Tasks

- Extract authentication/account state into a hook.
- Extract capability loading and refresh state into a hook.
- Extract document/index state into a hook.
- Extract chat send/RAG metadata handling into a hook.
- Preserve public component behavior.

### Testing Requirements

- Add hook-level tests where useful.
- Keep existing integration and accessibility tests passing.
- Run frontend lint, tests, and build.
- Run backend tests to preserve API expectations.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated, if applicable
- [ ] No new critical or high-severity issues introduced
- [ ] No user-facing workflow regressions

### Deliverables

- Focused frontend hooks.
- Smaller `App.jsx`.
- Updated tests.

### Risks or Blockers

- Local storage behavior can regress during state extraction.
- Async refresh behavior may become harder to reason about.

## Phase 8: Backend Service Boundary Cleanup

### Objective

Clarify backend service boundaries and remove stale scaffold ambiguity.

### Why This Phase Matters

The backend has real implementations alongside scaffold modules that still
say "not implemented in this phase." Future contributors need clear ownership
boundaries.

### Implementation Tasks

- Review `backend/app/ai/*` scaffold modules and real implementations.
- Remove or rename stale scaffolds when safe.
- Make provider interfaces explicit and documented.
- Ensure dependency injection remains testable.

### Testing Requirements

- Add or update unit tests around provider boundaries.
- Run backend tests.
- Run frontend tests if response contracts change.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] Service ownership is clearer than before

### Deliverables

- Cleaned service/provider boundaries.
- Updated architecture documentation.
- Regression tests.

### Risks or Blockers

- Over-cleaning could accidentally change runtime behavior.
- Some scaffold files may still be useful as future extension points.

## Phase 9: Document Pipeline Hardening

### Objective

Harden document upload, extraction, chunking, indexing, and search for common
failure modes.

### Why This Phase Matters

Document workflows are central to local RAG. They need strong validation,
clear errors, and reliable artifact handling before larger retrieval work.

### Implementation Tasks

- Audit document ID, conversation ID, file type, size, and path validation.
- Improve extraction and chunking warnings.
- Add artifact consistency checks.
- Add tests for failed processing, malformed artifacts, and missing files.

### Testing Requirements

- Unit tests for document service edge cases.
- API tests for upload/process/index/search errors.
- Regression tests for existing happy paths.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] Document failures are safe and explainable

### Deliverables

- Hardened document service.
- Expanded document tests.
- Updated API docs for errors and warnings.

### Risks or Blockers

- PDF parser behavior can vary by environment.
- Large-file tests must stay fast and deterministic.

## Phase 10: Retrieval Quality and Source Reliability

### Objective

Improve retrieval correctness, source metadata consistency, and source display
reliability.

### Why This Phase Matters

RAG answers are only useful if retrieved chunks are relevant and sources are
stable, honest, and easy to inspect.

### Implementation Tasks

- Audit source numbering through retrieval, reranking, and compression.
- Add tests for source ordering and omitted/trimmed context.
- Improve source previews and metadata normalization.
- Document retrieval limits and scoring fields.

### Testing Requirements

- Backend tests for retrieval ordering and source metadata.
- Frontend tests for source indicators and details.
- Regression tests for non-RAG chat.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] Source metadata remains stable across RAG modes

### Deliverables

- More reliable source metadata.
- Retrieval/source regression tests.
- Updated docs.

### Risks or Blockers

- Retrieval quality improvements may change expected ordering.
- UI may need careful handling of long source names.

## Phase 11: Real Vector Store Adapter Layer

### Objective

Add a clean adapter layer for real vector database backends without replacing
the local JSON store.

### Why This Phase Matters

This phase has been superseded by the Qdrant standardization work: Qdrant is
the active vector database, JSON remains an internal fallback, and the UI no
longer exposes vector database choice.

### Implementation Tasks

- Define vector store interface capabilities and health checks.
- Keep JSON as the default local fallback.
- Add one real backend adapter behind configuration, starting with the least
  operationally heavy option.
- Update component metadata based on actual backend availability.

### Testing Requirements

- Unit tests for adapter selection.
- Contract tests shared by JSON and new adapters.
- Integration tests that skip cleanly when optional dependencies are missing.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] JSON store behavior remains the default and still passes tests

### Deliverables

- Vector store interface.
- First real vector backend adapter.
- Tests and docs.

### Risks or Blockers

- Optional native dependencies may complicate installation.
- External service-backed stores need lifecycle documentation.

## Phase 12: OCR Expansion

### Objective

Implement real OCR processing for scanned PDFs and image-like PDF pages.

### Why This Phase Matters

OCR engines are discoverable, but broad OCR execution is incomplete. Scanned
documents need a reliable local path.

### Implementation Tasks

- Define OCR provider interface.
- Implement one or more local OCR providers behind availability checks.
- Add PDF fallback flow for low-text extraction.
- Surface OCR warnings and selected provider metadata.

### Testing Requirements

- Unit tests for OCR provider selection and fallback.
- Fixture-based tests for low-text PDFs.
- Skipped integration tests for optional OCR tools.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] Missing OCR tools never break document processing unexpectedly

### Deliverables

- OCR provider implementation.
- OCR tests and fixtures.
- Updated capability metadata and docs.

### Risks or Blockers

- OCR dependencies can be heavy.
- OCR quality is environment-dependent and should not be over-promised.

## Phase 13: Vision Chat

### Objective

Add local vision chat support for discovered multimodal Ollama models.

### Why This Phase Matters

Vision models are discoverable but currently discovery-only. This phase turns
that into an intentional, tested feature.

### Implementation Tasks

- Add image attachment handling in the frontend.
- Add backend request schema for vision prompts.
- Implement Ollama vision provider support.
- Keep text-only chat behavior unchanged.

### Testing Requirements

- Backend schema and provider tests.
- Frontend tests for image attachment controls.
- Integration tests with fake Ollama vision responses.
- Optional live Ollama vision smoke test.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] Text-only chat remains unchanged

### Deliverables

- Vision chat flow.
- Tests and docs.
- Updated capability metadata.

### Risks or Blockers

- Vision model APIs may differ across Ollama models.
- Image size and privacy handling need careful limits.

## Phase 14: Streaming Responses and Runtime Events

### Objective

Add streaming chat responses and clearer runtime progress events.

### Why This Phase Matters

Local models can be slow. Streaming improves perceived responsiveness and
gives users better feedback during generation, indexing, and model operations.

### Implementation Tasks

- Add backend streaming support for Ollama generation.
- Update frontend chat state for partial assistant messages.
- Add progress events for long document/index operations where appropriate.
- Keep non-streaming fallback behavior available.

### Testing Requirements

- Backend streaming tests with fake providers.
- Frontend tests for partial message rendering.
- Regression tests for errors mid-stream.

### Verification Checklist

Before proceeding to the next phase, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] Streaming failures degrade safely

### Deliverables

- Streaming chat implementation.
- Progress event support.
- Tests and docs.

### Risks or Blockers

- Streaming error handling can be subtle.
- UI state must avoid duplicate or corrupted assistant messages.

## Phase 15: Production Hardening and Release Readiness

### Objective

Prepare the project for a stable public release and safer self-hosted use.

### Why This Phase Matters

After feature and architecture stabilization, the project needs security,
operational, and release polish.

### Implementation Tasks

- Add deployment hardening guidance for reverse proxies and HTTPS.
- Review auth/session behavior and trusted-network assumptions.
- Add backup/restore documentation for local data.
- Add release checklist and versioned changelog.
- Review dependency update process and security scanning.

### Testing Requirements

- Full backend and frontend tests.
- Dockerized test suite.
- Smoke tests for production build.
- Manual deployment checklist.

### Verification Checklist

Before considering the roadmap complete, all of the following must be true:

- [ ] Code builds successfully
- [ ] Existing tests pass
- [ ] New tests for this phase pass
- [ ] Linting/static checks pass, if available
- [ ] Documentation updated
- [ ] No new critical or high-severity issues introduced
- [ ] Release checklist is complete

### Deliverables

- Release checklist.
- Hardening documentation.
- Changelog.
- Final verification report.

### Risks or Blockers

- Public internet exposure is still outside the default trust model.
- Security claims must stay conservative and accurate.

# Recommended Execution Rules

- Do not begin a new phase until the current phase has been implemented,
  tested, reviewed, and verified.
- Keep changes small and reviewable.
- Run the full backend and frontend test suite at the end of every phase.
- Update documentation as behavior changes.
- Add or update tests for every behavior change.
- Record verification results before proceeding.
- Keep optional live Ollama tests opt-in.
- If a phase reveals major architectural problems, pause and revise this
  roadmap before continuing.

# Suggested First Actions

1. Finish Phase 5 and commit the roadmap with the hygiene cleanup.
2. Confirm CI scope for Phase 6.
3. Decide whether Docker tests should be required in CI or reserved for manual
   verification.
4. Audit current frontend state ownership before Phase 7.
5. Keep `docs/verification-log.md` updated after every phase.
