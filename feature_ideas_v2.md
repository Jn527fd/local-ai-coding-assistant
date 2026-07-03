# Feature Ideas v2: Ranked Ideas for the Next Public Release

This document ranks feature ideas from most impactful to least impactful for
the next public release. It is based on a review of the current repository
after the Phase 15 release-readiness baseline.

Current baseline observed in the codebase:

- FastAPI backend with routers for auth, account, models, components,
  documents, chat, repositories, and health.
- React/Vite frontend with browser-local chats, per-chat AI settings,
  streaming chat, document workflows, and workspace UI.
- Local Ollama chat, embeddings, reranking, vision chat, context compression,
  component discovery, and optional live smoke tests.
- Document upload, PDF/text extraction, chunking, JSON vector indexes,
  retrieval-only search, RAG chat, source metadata, and OCRmyPDF low-text PDF
  fallback.
- Legacy repository keyword RAG still separate from document vector RAG.
- Docker Compose, Docker test services, release-hardening docs, backup docs,
  security docs, changelog, and roadmap v2.

Ranking principles:

- Prioritize public-release confidence, user data safety, and debuggability.
- Prefer features that reduce support burden and confusion.
- Prefer features that make current capabilities reliable before adding broad
  new AI surfaces.
- Keep the default path local, CPU-friendly, and private.

## 1. Server-Side Conversation Persistence

Impact: Very high

Move chats, messages, settings, source metadata, and attachment references from
browser-only localStorage into an optional backend data store.

Why it matters:

- Current browser-local chats are easy to lose and hard to back up.
- Per-chat settings now matter enough that they should be portable.
- Public users will expect conversations to survive browser resets and move
  with the app data directory.

Suggested scope:

- Add local JSON or SQLite persistence under `data/`.
- Preserve localStorage as a migration source and fallback.
- Add import/export for conversations.
- Add delete, rename, archive, and retention semantics.

Key tests:

- Migration from existing localStorage records.
- Corrupt/missing conversation records.
- Backup/restore fixture.
- Frontend persistence and refresh behavior.

## 2. Background Jobs and Progress UI

Impact: Very high

Add a backend job system for document processing, indexing, OCR, repository
indexing, model/capability checks, and long RAG preparation work.

Why it matters:

- Document indexing and OCR can take long enough to feel frozen.
- Streaming exists for chat, but broader runtime progress is limited.
- Job IDs, cancellation, and status would make the app feel much more stable.

Suggested scope:

- Add in-process job registry first.
- Expose job status, logs, warnings, progress percentage, and cancellation.
- Show progress in the existing workspace UI without a redesign.
- Keep jobs local and durable enough to recover basic status after refresh.

Key tests:

- Job lifecycle unit tests.
- API tests for pending/running/succeeded/failed/cancelled.
- Frontend progress rendering tests.
- Regression tests for existing synchronous paths.

## 3. Release Candidate Quality Gate Dashboard

Impact: Very high

Add an in-app and CLI-visible readiness dashboard that checks backend health,
Ollama reachability, models, local tools, writable data paths, Docker config,
and release-critical settings.

Why it matters:

- The project has many optional local capabilities.
- Users need a clear answer to "what is working on this machine?"
- It reduces support friction for OCR/parser/vector/model detection issues.

Suggested scope:

- Add `/diagnostics/readiness`.
- Show pass/warn/fail checks with exact remediation text.
- Include data directory permissions, credentials presence, API key status,
  Ollama tags, selected model availability, OCR/PDF tool availability, and
  vector backend health.
- Add a "copy diagnostics" button that excludes secrets.

Key tests:

- Backend diagnostics with mocked healthy/unhealthy dependencies.
- Frontend rendering for pass/warn/fail states.
- Secret-redaction tests.

## 4. Document Ingestion v2

Impact: Very high

Make document ingestion more transparent, resumable, and complete.

Why it matters:

- Current document workflows support `.txt`, `.md`, and `.pdf`, but broad OCR
  and parser expansion are early.
- Public users need clear per-document status and actionable errors.

Suggested scope:

- Add per-document pipeline stages: uploaded, extracted, OCR attempted,
  chunked, indexed, searchable.
- Add retry/reprocess actions.
- Store extraction warnings and parser/OCR metadata.
- Add page-level PDF metadata where available.
- Improve duplicate file handling and document replacement.

Key tests:

- Stage transitions.
- Parser failure recovery.
- Low-text PDF OCR fallback.
- Reprocess and delete behavior.

## 5. Unified Document and Repository RAG

Impact: Very high

Bring repository knowledge into the same retrieval architecture as uploaded
documents while preserving the legacy keyword API during migration.

Why it matters:

- The product is a coding assistant, but repository RAG remains keyword-based.
- Unified retrieval unlocks shared sources, reranking, context compression, and
  evaluation across docs and code.

Suggested scope:

- Index repositories into the vector pipeline as collections.
- Keep legacy repository keyword search available as compatibility mode.
- Include file path, symbol, language, and line metadata in sources.
- Allow a chat to select document collections, repository collections, or both.

Key tests:

- Repository vector indexing.
- Mixed document/repo retrieval.
- Source metadata and citation stability.
- Legacy repository API regression tests.

## 6. Retrieval Quality Evaluation Suite

Impact: Very high

Add a small local evaluation harness for retrieval and RAG behavior.

Why it matters:

- RAG can appear to work while silently retrieving poor context.
- Evaluation protects future changes to chunking, reranking, vector stores, and
  prompt construction.

Suggested scope:

- Add golden test corpora and expected source matches.
- Measure hit rate, source rank, citation presence, and warning behavior.
- Include CLI command and CI-safe fake embedding mode.
- Keep live Ollama quality tests optional.

Key tests:

- Deterministic fake embedding retrieval tests.
- Reranker ordering checks.
- Prompt/source integrity checks.
- CI summary artifact or JSON report.

## 7. Production Vector Store Adapters

Impact: High

Promote vector store support from JSON-first with early adapters to reliable
local backends.

Why it matters:

- JSON indexes are inspectable but limited for larger corpora.
- The UI already exposes vector database choices, so users need accurate
  behavior and clear fallbacks.

Suggested scope:

- Finish Chroma adapter behavior.
- Add FAISS as a CPU-friendly local backend.
- Keep Qdrant and LanceDB behind availability checks until stable.
- Add migration or rebuild guidance between stores.

Key tests:

- Adapter contract tests shared by JSON/Chroma/FAISS.
- Missing dependency fallback tests.
- Index/search/delete parity tests.

## 8. Source Inspector and Citation QA

Impact: High

Improve source transparency for RAG answers without redesigning the whole UI.

Why it matters:

- The app already returns source metadata, vector scores, rerank scores, and
  final ranks.
- Public users need to inspect why an answer was grounded in a passage.

Suggested scope:

- Add a source details drawer or modal.
- Show document name, chunk index, vector score, rerank score, final rank,
  omitted/trimmed status, and text preview.
- Add "open document metadata" and "copy citation" actions.

Key tests:

- Source rendering with and without rerank scores.
- Compression-trimmed source behavior.
- Keyboard and accessibility checks.

## 9. Repository Lifecycle Management

Impact: High

Add safe repository add, refresh, remove, and freshness controls.

Why it matters:

- Users currently clone repositories outside the app and point the backend at a
  path.
- Public users will need to know whether an index is stale.

Suggested scope:

- Add repository records under `data/`.
- Track indexed commit/hash or file snapshot metadata.
- Add refresh and delete actions.
- Keep mounts read-only by default.
- Defer remote GitHub cloning until path-based lifecycle is solid.

Key tests:

- Path validation.
- Refresh after file changes.
- Delete cleans generated indexes only.
- Docker mount behavior.

## 10. Language-Aware Code Parsing

Impact: High

Use Tree-sitter or another parser to chunk source code by symbols instead of
plain text windows.

Why it matters:

- Better code chunks improve repository Q&A much more than generic chunking.
- Symbol metadata also improves citations and future agent workflows.

Suggested scope:

- Start with Python and JavaScript/TypeScript.
- Extract functions, classes, imports, docstrings, and line ranges.
- Fall back to current chunking when parsing fails.

Key tests:

- Parser fixtures for supported languages.
- Fallback behavior for invalid syntax.
- Source metadata line range tests.

## 11. In-App Backup, Restore, and Export

Impact: High

Turn backup/restore documentation into an app-supported workflow.

Why it matters:

- Local-first apps succeed when users trust that their data is recoverable.
- The app already has a clear `data/` storage model.

Suggested scope:

- Export credentials warning, app settings, conversations, uploads, indexes,
  and repository records as a local archive.
- Restore with dry-run validation.
- Add selective export for chats and documents.

Key tests:

- Archive creation.
- Restore dry run.
- Secret redaction in export manifests.
- Cross-platform path handling.

## 12. Configuration and Model Setup Assistant

Impact: High

Add guided setup for tiny smoke models, recommended local model sets, API key
status, and capability refresh.

Why it matters:

- Users often get stuck on model/tool availability before trying the app.
- The project already supports CPU-friendly live Ollama smoke tests.

Suggested scope:

- Add setup checks for `smollm2:135m`, `all-minilm`, and optional reranker or
  vision model.
- Never pull large models automatically.
- Provide copyable Ollama commands and clear "installed/not installed" state.

Key tests:

- Capability status rendering.
- Missing Ollama behavior.
- No automatic pull behavior.

## 13. Runtime Resource Controls

Impact: Medium-high

Add limits and controls for local CPU/RAM pressure.

Why it matters:

- Local AI workloads can overload a laptop.
- Sequential reranking and OCR can be slow or expensive.

Suggested scope:

- Per-operation candidate limits and timeout display.
- User-visible queue depth.
- Cancel running job.
- Optional "low resource mode" defaults.

Key tests:

- Timeout and cancellation behavior.
- Limits enforced in request validation.
- UI disabled states.

## 14. Observability and Diagnostics Bundle

Impact: Medium-high

Add structured request IDs, local logs, and a safe diagnostics export.

Why it matters:

- Local deployments are hard to debug without seeing logs and configuration.
- Public users need a safe way to share issue context without leaking prompts
  or secrets.

Suggested scope:

- Add request IDs to backend logs and responses.
- Add redacted diagnostics bundle endpoint.
- Include version, settings summary, capabilities, recent warnings, and test
  command hints.

Key tests:

- Redaction tests.
- Request ID propagation.
- Diagnostics schema tests.

## 15. Frontend State Decomposition

Impact: Medium-high

Extract focused hooks and state modules from `frontend/src/App.jsx`.

Why it matters:

- `App.jsx` currently owns authentication, API key, chats, documents, indexes,
  search, sending, dialogs, toasts, navigation, and command state.
- Smaller modules will make future features safer to add.

Suggested scope:

- Extract `useAuthSession`, `useChatStore`, `useDocumentWorkspace`,
  `useChatSending`, and `useToasts`.
- Preserve existing UI and tests.
- Avoid global state libraries until the local patterns are clear.

Key tests:

- Existing integration tests unchanged.
- Hook-level tests for extracted behavior.
- No localStorage migration regression.

## 16. Semantic and Memory Compression

Impact: Medium

Implement the currently fallback-only `semantic` and `memory` context
compression modes.

Why it matters:

- The settings UI already exposes these modes as planned/fallback behavior.
- Long-running local conversations will need better memory than trimming.

Suggested scope:

- Add memory summaries stored per conversation once server-side persistence
  exists.
- Add semantic selection only after embeddings and evaluation are stable.
- Preserve latest user message and source metadata invariants.

Key tests:

- Summary persistence.
- Prompt construction invariants.
- Fallback behavior on model failure.

## 17. OCR Engine Expansion

Impact: Medium

Wire more detected OCR engines into the document pipeline after job tracking is
available.

Why it matters:

- The registry detects tools such as Tesseract, PaddleOCR, EasyOCR, OCRmyPDF,
  and Docling, but execution is limited.
- OCR work needs progress, warnings, and retries to be user-friendly.

Suggested scope:

- Add Tesseract image/PDF page execution.
- Add Docling parser/OCR path where installed.
- Keep PaddleOCR/EasyOCR optional due heavier dependencies.

Key tests:

- Missing binary/package skips.
- Low-text PDF routing.
- OCR warnings and text quality metadata.

## 18. Vision Chat UX Improvements

Impact: Medium

Improve image attachment handling around the existing vision chat path.

Why it matters:

- Vision chat exists, but users need clearer feedback on model compatibility,
  image size, preview, and failure modes.

Suggested scope:

- Add per-image status and remove/replace controls.
- Warn when no valid vision model is selected.
- Add optional live vision smoke docs in the setup assistant.

Key tests:

- Attachment validation.
- Vision model unavailable fallback.
- Frontend preview/removal tests.

## 19. Prompt and Profile Templates

Impact: Medium

Let users save local prompt profiles for coding, summarization, debugging,
document QA, and repository review.

Why it matters:

- Templates make the tool feel useful before advanced agent behavior exists.
- They are low-risk if stored locally and scoped per conversation.

Suggested scope:

- Add local profiles under `data/` or conversation settings.
- Include system prompt, preferred model settings, RAG defaults, and
  compressor/reranker preferences.
- Add import/export.

Key tests:

- Template save/load/delete.
- Applying a template does not erase messages.
- Invalid settings resolve safely.

## 20. Retrieval Playground

Impact: Medium

Add a developer-facing panel to compare retrieval settings before using them in
chat.

Why it matters:

- Users can tune topK, candidateK, reranker, chunker, and vector backend
  without repeatedly sending chat prompts.

Suggested scope:

- Reuse document search endpoint and expose advanced options.
- Show raw retrieved chunks, scores, warnings, and final prompt order.
- Add copyable debug JSON.

Key tests:

- Search option request schema.
- Rendering vector/rerank scores.
- Warning display.

## 21. Local Model Benchmark Smoke

Impact: Medium-low

Add optional local timing checks for selected chat, embedding, reranker, and
vision models.

Why it matters:

- Public users need to know whether a selected model is practical on their
  hardware.
- This should validate wiring and rough latency, not model quality.

Suggested scope:

- Opt-in benchmark command and UI action.
- Record latency, tokens/second when available, embedding latency, and failure
  reasons.
- Keep results local.

Key tests:

- Fake Ollama benchmark behavior.
- Skip behavior when live Ollama is disabled.
- UI rendering for slow/unavailable models.

## 22. Safer Remote Access Presets

Impact: Medium-low

Provide example reverse proxy configurations and a config validator for remote
trusted access.

Why it matters:

- The project should remain honest about not being public-internet hardened,
  while still helping careful self-hosters.

Suggested scope:

- Add Caddy and Nginx examples.
- Add `SESSION_COOKIE_SECURE` and CORS validation hints.
- Add docs for Tailscale/WireGuard-style access.

Key tests:

- Documentation hygiene.
- Config parser tests if examples become templates.

## 23. Chat and Document Export

Impact: Medium-low

Export conversations, answers, sources, and document metadata to Markdown or
JSON.

Why it matters:

- Users will want to preserve useful answers outside the app.
- Export is safer after server-side persistence exists.

Suggested scope:

- Export one chat to Markdown with citations.
- Export all chat data to JSON.
- Include source previews and model/settings metadata.

Key tests:

- Markdown output snapshots.
- Redaction or opt-in handling for source text.
- Browser download behavior.

## 24. Command Palette Expansion

Impact: Medium-low

Turn the existing command palette into a real workflow launcher.

Why it matters:

- The app already has a command palette.
- It can expose power-user actions without redesigning the UI.

Suggested scope:

- Commands for new chat, upload document, refresh capabilities, run readiness
  check, export chat, open release docs, and focus search.
- Keyboard-first navigation.

Key tests:

- Command filtering.
- Keyboard activation.
- Disabled/unavailable command states.

## 25. Lightweight Plugin/Adapter Manifest

Impact: Low-medium

Introduce a local manifest format for optional adapters and capabilities.

Why it matters:

- The backend already has many adapter categories.
- A manifest could make future tools discoverable without hardcoding every
  label and warning.

Suggested scope:

- Keep it internal/local at first.
- Describe adapter id, type, package/binary checks, execution status, and docs.
- Do not execute untrusted plugin code.

Key tests:

- Manifest validation.
- Capability registry integration.
- Invalid manifest ignored safely.

## 26. Onboarding Checklist

Impact: Low-medium

Add a small first-run checklist for account setup, API key, model discovery,
document upload, and first RAG query.

Why it matters:

- It smooths first impressions without changing core functionality.
- It can reuse readiness and setup checks.

Suggested scope:

- Show only when setup is incomplete.
- Let users dismiss it.
- Link to local docs.

Key tests:

- Checklist state rendering.
- Dismiss behavior.
- Accessibility checks.

## 27. UI Theme and Layout Polish

Impact: Low

Polish spacing, responsive behavior, empty states, and visual consistency after
core reliability work.

Why it matters:

- The UI is already usable; polish helps public perception but should not come
  before data durability and diagnostics.

Suggested scope:

- Tighten mobile/tablet layouts.
- Review long labels in settings controls.
- Add consistent loading skeletons.
- Keep the current product UI rather than a landing page redesign.

Key tests:

- Accessibility tests.
- Visual smoke tests.
- Responsive manual QA.

## 28. Optional Desktop Packaging Research

Impact: Low

Evaluate whether a desktop wrapper would improve local-first distribution.

Why it matters:

- A desktop app could simplify local use, but it also adds packaging and update
  complexity.

Suggested scope:

- Research only for the next public release.
- Compare Docker Compose, scripts, and desktop wrapper tradeoffs.
- Do not commit to packaging until backend/frontend release stability improves.

Key tests:

- None for research; document findings and risks.

## Recommended Public Release Feature Set

For the next public release, the best balance is:

1. Server-side conversation persistence.
2. Background jobs and progress UI.
3. Readiness dashboard and diagnostics.
4. Document ingestion v2.
5. Unified document and repository RAG foundation.
6. Retrieval quality evaluation suite.
7. Source inspector and citation QA.

This set improves trust, durability, observability, and the core value of a
local coding assistant without taking on too many new AI surfaces at once.

## Features to Avoid Until Later

- Autonomous code editing agents.
- Public multi-tenant hosting.
- Automatic pulling of large models.
- Remote repository write operations.
- Cloud sync.
- Marketplace-style third-party plugin execution.

These ideas may be useful eventually, but they would expand the trust and
safety surface before the local-first foundation is ready.
