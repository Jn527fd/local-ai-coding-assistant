# Roadmap v2: Next 15 Phases for the Next Public Release

This roadmap starts after the Phase 15 release-readiness baseline. The current
project is a local, trusted-network AI workspace with Ollama chat, per-chat AI
settings, document ingestion, local JSON vector indexes, RAG, reranking,
context compression, OCRmyPDF fallback, vision chat, streaming responses,
Docker Compose, CI, and release-hardening documentation.

The next public release should prioritize reliability, data durability,
retrieval quality, security boundaries, and operational clarity before adding
large new feature surfaces.

## Repository Review Snapshot

Current strengths:

- Clear FastAPI router/service structure with dependency-injected tests.
- Hermetic default backend and frontend tests that do not require Ollama.
- Per-conversation settings and component capability discovery.
- Document upload, processing, indexing, retrieval, RAG, reranking,
  compression, OCR fallback, vision chat, and streaming are present.
- Docker Compose and GitHub Actions cover the core local development path.
- Release-hardening, backup, dependency, and security docs now exist.

Current limits to address:

- Browser-local chat storage limits portability, backups, and multi-device use.
- JSON vector storage is transparent but not scalable for larger corpora.
- Chroma is optional and early; other vector backends are still placeholders.
- OCR execution is limited to OCRmyPDF PDF fallback.
- Streaming exists for chat but not all long-running document/index/model
  operations.
- Repository RAG remains keyword-based and separate from document RAG.
- Security posture is trusted-network first; public exposure requires more
  controls.
- Frontend state is concentrated in `App.jsx` and should be decomposed.
- There is no formal retrieval evaluation suite or quality benchmark.

## Phase 1: Release Candidate Stabilization

### Objective

Stabilize the current feature set as a clean release candidate.

### Implementation Tasks

- Freeze feature scope for the release candidate.
- Audit README, API docs, setup docs, and screenshots for accuracy.
- Fix stale copy such as completed features still listed as future work.
- Add a release-candidate checklist entry to `CHANGELOG.md`.
- Confirm all example configuration files are safe.

### Testing Requirements

- Full backend pytest.
- Full frontend lint, tests, and build.
- Docker backend and frontend test services.
- Manual smoke through browser and Docker Compose.

### Verification Checklist

- [ ] Existing tests pass.
- [ ] Docker tests pass or blockers are documented.
- [ ] Release docs match current behavior.
- [ ] No stale "not implemented" claims for implemented features.
- [ ] No local secrets or generated data are tracked.

### Deliverables

- Release-candidate docs update.
- Finalized changelog section.
- Recorded verification log.

### Risks or Blockers

- Docker availability can vary by developer machine.
- Documentation may lag code unless checked deliberately.

## Phase 2: Server-Side Conversation Persistence

### Objective

Move optional conversation persistence from browser-only localStorage to a
local backend data store while preserving browser-local behavior as a fallback.

### Implementation Tasks

- Design a local conversation schema for chats, messages, settings, metadata,
  and attachment references.
- Add a backend conversation service scoped by authenticated local user.
- Add import/export and migration from browser localStorage.
- Add retention limits and delete semantics.
- Keep current browser-local mode available behind a setting if needed.

### Testing Requirements

- Unit tests for persistence service.
- API tests for create/list/update/delete conversations.
- Frontend migration and persistence tests.
- Backup/restore test fixture for persisted conversations.

### Verification Checklist

- [ ] Existing localStorage chats migrate safely.
- [ ] Deleted chats are not used in prompts.
- [ ] Backup docs include conversation storage.
- [ ] Tests cover corrupt/missing conversation records.

### Deliverables

- Conversation persistence API.
- Frontend persistence integration.
- Migration and export/import docs.

### Risks or Blockers

- Storage format choice affects later multi-user and sync work.
- Migration must avoid losing existing browser chats.

## Phase 3: Local Data Store and Migration Layer

### Objective

Introduce a small durable local database layer for app metadata currently
spread across JSON files.

### Implementation Tasks

- Choose SQLite or another local embedded store for metadata.
- Define migrations for users, settings, conversations, documents, indexes,
  and jobs.
- Keep generated vector payloads in files or adapter stores as appropriate.
- Add migration CLI and startup migration checks.
- Document backup implications.

### Testing Requirements

- Migration unit tests.
- Upgrade/downgrade or forward-only migration tests.
- Corrupt database handling tests.
- Docker volume migration smoke.

### Verification Checklist

- [ ] Fresh install works.
- [ ] Existing JSON config migration works.
- [ ] Failed migration stops safely with actionable error.
- [ ] Backup/restore docs are updated.

### Deliverables

- Local metadata store.
- Migration tooling.
- Updated operational docs.

### Risks or Blockers

- Migration bugs can affect user data.
- JSON compatibility needs careful transition planning.

## Phase 4: Background Jobs and Runtime Progress

### Objective

Move long-running document processing, indexing, OCR, and model operations into
tracked background jobs with progress events.

### Implementation Tasks

- Add a local job model and job service.
- Add progress events for upload processing, extraction, chunking, embedding,
  indexing, OCR, and reranking where applicable.
- Add cancellation for safe job types.
- Expose job status endpoints and frontend progress UI.
- Keep synchronous paths available where simple.

### Testing Requirements

- Unit tests for job state transitions.
- API tests for job creation/status/cancellation.
- Frontend tests for progress states and failures.
- Regression tests for existing document endpoints.

### Verification Checklist

- [ ] Long operations report useful progress.
- [ ] Failed jobs are visible and explainable.
- [ ] Cancellation does not corrupt artifacts.
- [ ] Existing synchronous tests still pass.

### Deliverables

- Job service.
- Progress events and UI.
- Job docs.

### Risks or Blockers

- Background execution can introduce race conditions.
- Cancellation semantics must be conservative.

## Phase 5: Document Ingestion v2

### Objective

Expand document ingestion reliability and supported file coverage.

### Implementation Tasks

- Add file-type sniffing beyond extension checks.
- Add DOCX, HTML, and CSV/TSV extraction where local dependencies are safe.
- Add OCR provider adapters beyond OCRmyPDF only when available.
- Add extraction quality metadata and per-page diagnostics.
- Add duplicate document detection.

### Testing Requirements

- Fixture tests for each supported file type.
- OCR provider selection and skip tests.
- Malformed file tests.
- Large-file and chunk-limit tests.

### Verification Checklist

- [ ] Unsupported files fail clearly.
- [ ] Extraction metadata is reliable.
- [ ] Missing optional tools never break default processing.
- [ ] Existing PDF/text behavior is preserved.

### Deliverables

- Expanded parser adapters.
- OCR provider expansion.
- Document diagnostics UI.

### Risks or Blockers

- Parser dependencies may be heavy.
- OCR quality varies widely by environment.

## Phase 6: Vector Store Production Adapters

### Objective

Graduate vector storage from JSON-first testing to reliable optional backends.

### Implementation Tasks

- Complete Chroma adapter contract.
- Add Qdrant and LanceDB adapters if dependency and deployment costs are
  acceptable.
- Add collection migration/export/import utilities.
- Add vector backend health and diagnostics endpoints.
- Document backend-specific deployment requirements.

### Testing Requirements

- Adapter contract tests.
- Optional integration tests gated by installed dependencies or services.
- Migration tests from JSON to adapter.
- RAG regression tests across backends.

### Verification Checklist

- [ ] JSON remains default and safe.
- [ ] Optional backends skip cleanly when unavailable.
- [ ] Collection metadata is consistent across backends.
- [ ] RAG source metadata stays stable.

### Deliverables

- Production vector adapter layer.
- Migration tooling.
- Backend docs and health UI.

### Risks or Blockers

- External services can complicate Docker defaults.
- Backend-specific metadata can drift.

## Phase 7: Retrieval Quality Evaluation

### Objective

Add repeatable retrieval and RAG quality evaluation before tuning algorithms.

### Implementation Tasks

- Create a small local evaluation corpus.
- Add expected retrieval/source fixtures.
- Measure recall, rank position, source accuracy, and warning behavior.
- Add configurable RAG prompt templates for comparison.
- Record results in CI or optional eval commands.

### Testing Requirements

- Deterministic retrieval eval tests with fake embeddings.
- Optional live embedding eval smoke.
- Regression tests for prompt source numbering.
- Snapshot tests for source metadata shape.

### Verification Checklist

- [ ] Eval corpus is committed and non-sensitive.
- [ ] Metrics are stable under fake providers.
- [ ] Live eval is opt-in.
- [ ] Prompt changes require eval review.

### Deliverables

- Retrieval eval harness.
- RAG quality baseline.
- Prompt tuning docs.

### Risks or Blockers

- Live model quality is nondeterministic.
- Metrics can be misleading without careful fixtures.

## Phase 8: Unified Repository Intelligence

### Objective

Bring repository RAG closer to document RAG without breaking the legacy keyword
API.

### Implementation Tasks

- Add repository document records and collection metadata.
- Add optional repository embeddings through the document vector pipeline.
- Add index freshness detection.
- Add safe local Git clone/update workflows.
- Preserve `/repos/index-local` and `/repos/ask`.

### Testing Requirements

- Repository indexing regression tests.
- Git clone/update tests with local fixtures.
- Vector repository retrieval tests.
- Freshness and stale-index tests.

### Verification Checklist

- [ ] Legacy keyword repository RAG still works.
- [ ] Vector repository indexing is opt-in.
- [ ] Repository paths stay inside allowed roots.
- [ ] Freshness warnings are clear.

### Deliverables

- Unified repository/document retrieval option.
- Repository lifecycle controls.
- Updated repo docs.

### Risks or Blockers

- Repository indexing can touch many files.
- Git operations require strict path and network controls.

## Phase 9: Language-Aware Code Parsing

### Objective

Improve source-code chunking and metadata with language-aware parsing.

### Implementation Tasks

- Evaluate Tree-sitter or lightweight language parsers.
- Add symbol-aware chunks for common languages.
- Preserve line ranges and file metadata.
- Add fallback line chunking when parsers are unavailable.
- Surface symbols in source citations.

### Testing Requirements

- Parser fixture tests for Python, JS/TS, Markdown, JSON/YAML, HTML, and CSS.
- Fallback tests when parser packages are missing.
- RAG source metadata tests.
- Performance tests for larger repositories.

### Verification Checklist

- [ ] Parser failures fall back safely.
- [ ] Line ranges remain accurate.
- [ ] Existing repository indexes remain readable or migratable.
- [ ] Source citations show useful symbol context.

### Deliverables

- Language-aware chunkers.
- Symbol metadata.
- Parser docs.

### Risks or Blockers

- Parser dependencies may be complex on Windows and Linux.
- Incorrect line metadata can erode trust.

## Phase 10: Frontend State and Component Architecture

### Objective

Reduce `App.jsx` complexity and make frontend workflows easier to maintain.

### Implementation Tasks

- Extract chat send/stream logic into hooks.
- Extract document workflow state into hooks.
- Extract account/settings state into hooks.
- Add focused component tests for each hook boundary.
- Keep visual behavior unchanged.

### Testing Requirements

- Hook unit tests.
- Existing integration and accessibility tests.
- Visual/manual smoke for chat, settings, and documents.
- Regression tests for localStorage migration.

### Verification Checklist

- [ ] No UI redesign is introduced accidentally.
- [ ] Existing workflows still pass.
- [ ] State ownership is documented.
- [ ] Components are smaller and easier to test.

### Deliverables

- Frontend hooks and smaller containers.
- Updated frontend architecture notes.
- Maintained test coverage.

### Risks or Blockers

- Refactors can introduce subtle state regressions.
- Tests should move with behavior, not implementation details.

## Phase 11: Accessibility, Mobile, and UX Polish

### Objective

Make the app easier to use across screen sizes and assistive technologies.

### Implementation Tasks

- Audit keyboard navigation for chat, settings, documents, and modals.
- Improve mobile layout for the composer, settings, and source citations.
- Add accessible status text for streaming, jobs, and warnings.
- Verify color contrast and focus states.
- Add screenshot-based manual QA notes.

### Testing Requirements

- Axe tests for major screens.
- Keyboard interaction tests.
- Responsive component tests where practical.
- Manual mobile viewport smoke.

### Verification Checklist

- [ ] Critical axe violations are zero.
- [ ] Core workflows are keyboard-accessible.
- [ ] Text does not overlap at mobile widths.
- [ ] Streaming/status updates are announced appropriately.

### Deliverables

- Accessibility fixes.
- Mobile polish.
- UX QA checklist.

### Risks or Blockers

- Visual changes can cascade through large CSS files.
- Automated accessibility tests do not replace manual review.

## Phase 12: Security Hardening v2

### Objective

Strengthen the trusted-network security model and prepare for safer remote
access behind a proxy.

### Implementation Tasks

- Add CSRF review and protections for session-cookie routes.
- Add optional persistent session signing key configuration.
- Add rate limits or lockouts for login attempts.
- Add API-key rotation UX.
- Add security headers through frontend/backend or reverse proxy docs.
- Add audit logging for auth and settings changes without leaking secrets.

### Testing Requirements

- Auth regression tests.
- CSRF and cookie behavior tests.
- Rate-limit tests.
- Security header tests where implemented.

### Verification Checklist

- [ ] Auth routes remain usable locally.
- [ ] Secrets are not logged.
- [ ] Security controls are documented.
- [ ] Public-internet limitations remain explicit.

### Deliverables

- Hardened auth/session behavior.
- API-key rotation.
- Security tests and docs.

### Risks or Blockers

- Security features can break local development if defaults are too strict.
- Claims must remain conservative.

## Phase 13: Observability and Diagnostics

### Objective

Give operators enough diagnostics to understand local model, document, and
retrieval behavior.

### Implementation Tasks

- Add structured diagnostic endpoints for runtime status.
- Add model, embedding, retrieval, reranking, compression, and streaming timing
  metadata where safe.
- Add redacted logs for job failures.
- Add frontend diagnostics panel.
- Add support bundle export that excludes secrets and prompt contents by
  default.

### Testing Requirements

- Unit tests for redaction.
- API tests for diagnostics endpoints.
- Frontend diagnostics rendering tests.
- Manual support bundle inspection.

### Verification Checklist

- [ ] Diagnostics never include secrets.
- [ ] Prompt/document content is excluded unless explicitly requested.
- [ ] Timing metadata is useful and bounded.
- [ ] Failure states are actionable.

### Deliverables

- Diagnostics API/UI.
- Redacted support bundle.
- Observability docs.

### Risks or Blockers

- Logs can accidentally leak content.
- Too much diagnostics UI can overwhelm normal users.

## Phase 14: Packaging and Deployment Templates

### Objective

Make installation and upgrades easier for non-developer self-hosters.

### Implementation Tasks

- Add a production Compose template with optional reverse proxy example.
- Add `.env` validation script.
- Add upgrade script that backs up data before container replacement.
- Add documented systemd unit examples if useful.
- Add release artifact checklist for screenshots and generated docs.

### Testing Requirements

- Script unit tests where practical.
- Docker Compose config validation.
- Manual clean-machine install smoke.
- Upgrade smoke from previous release data.

### Verification Checklist

- [ ] Clean install works from docs.
- [ ] Upgrade path preserves data.
- [ ] Misconfiguration errors are clear.
- [ ] Examples do not expose Ollama publicly.

### Deliverables

- Deployment templates.
- Upgrade tooling.
- Install/upgrade docs.

### Risks or Blockers

- Host environments differ widely.
- Automation must avoid destructive defaults.

## Phase 15: Public Release Candidate QA

### Objective

Complete the next public release candidate with documented verification and
known limitations.

### Implementation Tasks

- Freeze scope.
- Complete changelog and release notes.
- Run full local, Docker, and optional live smoke tests.
- Run manual UX, backup/restore, and deployment checklist.
- Tag the release candidate after verification.

### Testing Requirements

- Full backend tests.
- Full frontend lint/tests/build.
- Dockerized test suite.
- Optional live Ollama smoke on prepared hardware.
- Manual release checklist.

### Verification Checklist

- [ ] All release checklist items are complete or explicitly deferred.
- [ ] Changelog is accurate.
- [ ] Backup/restore instructions are verified.
- [ ] Security/trust-boundary docs are current.
- [ ] No critical or high-severity issues remain open for the release.

### Deliverables

- Release candidate tag.
- Final changelog.
- Verification log.
- Updated public docs.

### Risks or Blockers

- Hardware-specific model behavior may differ from development machines.
- Release should pause if trust-boundary or data-loss risks are discovered.

# Execution Rules

- Do not start a new phase until the current phase is implemented, tested, and
  recorded.
- Keep changes small enough to review.
- Preserve hermetic default tests.
- Keep live Ollama and heavyweight backend tests opt-in unless the release
  process explicitly changes.
- Update docs with every behavior change.
- Record verification results in `docs/verification-log.md`.
- Revisit this roadmap if a phase exposes a major architecture flaw.
