# Changelog

All notable project changes should be recorded here. This project follows a
simple versioned changelog format until formal semantic-version release
automation is added.

## [Unreleased]

### Added

- Optional backend conversation persistence with session-scoped JSON storage,
  browser-to-backend migration, import/export endpoints, and delete semantics.
- Local SQLite metadata catalogue with startup migrations, manual migration
  diagnostics, JSON metadata import, and conversation metadata mirroring.
- Local background job tracking for document processing and indexing, with
  progress/status endpoints, conservative cancellation, and minimal frontend
  progress display.
- Document ingestion v2 coverage for DOCX, HTML, CSV, and TSV uploads, with
  file-type sniffing, extraction diagnostics, duplicate detection, and clearer
  malformed-file errors.
- Vector store production adapter diagnostics, portable collection
  export/import, JSON-to-adapter migration endpoints, stronger Chroma adapter
  contract coverage, and explicit Qdrant/LanceDB deferrals.
- Deterministic retrieval quality evaluation harness with a non-sensitive
  fixture corpus, expected source fixtures, recall/rank/source metadata
  metrics, and warning-behavior coverage.
- Opt-in repository vector indexing/search, repository index freshness
  warnings, repository vector collection metadata, and configured local
  repository root validation while preserving legacy keyword repository RAG.
- Lightweight language-aware repository chunking for Python, JS/TS, Markdown,
  JSON/YAML, HTML, and CSS with symbol metadata and safe line-based fallback.
- Frontend workflow hooks for chat streaming, document operations, API key
  storage, and focused hook tests while preserving existing UI behavior.
- Accessibility and mobile polish for composer status announcements, document
  job progress, source citations, settings drawer focus, shared dialog focus,
  and narrow-screen document/source layouts.
- Security hardening for trusted-network deployments, including CSRF checks for
  unsafe session-cookie requests, optional signed session cookies, login
  rate-limiting, backend security headers, redacted audit logs, and API-key
  rotation UX.
- Metadata-only diagnostics and redacted support-bundle export for runtime,
  model, document, retrieval, vector, and job troubleshooting, plus a small
  frontend diagnostics panel.
- Production deployment template, environment validation tooling, and a
  backup-before-upgrade helper for safer self-hosted container replacement.

### Release Candidate Checklist

- [x] README landing page reviewed and refreshed for public preview wording.
- [x] Setup docs aligned with the JSON default and optional Chroma adapter.
- [x] Example configuration files reviewed for placeholders, empty secrets, and
  trusted-network defaults.
- [x] Release candidate notes drafted in `docs/release-notes-0.2.0-rc1.md`.
- [x] Stable v2 release notes drafted in `docs/release-notes-0.2.0.md`.
- [x] Support and hotfix guidance added in `docs/support.md`.
- [x] Local backend, frontend lint/build, script tests, compile checks, and
  docs/security/deployment audit completed for RC QA.
- [ ] Frontend Vitest and Docker verification pending on a non-sandboxed
  machine.
- [ ] Manual browser smoke, optional live Ollama smoke, and target-machine env
  validation pending.
- [ ] Final release tag and release date pending after full release-candidate
  verification.

## [0.1.0] - 2026-07-03

### Added

- Local Ollama chat with per-conversation AI component settings.
- Component discovery for local LLMs, embedders, rerankers, vision models, OCR
  engines, PDF parsers, chunkers, vector databases, RAG pipelines, and context
  compressors.
- Document upload, PDF/text extraction, chunking, local JSON vector indexing,
  retrieval-only search, RAG chat, source metadata, optional reranking, and
  optional context compression.
- OCRmyPDF fallback for low-text PDFs when selected and available.
- Vision chat path for selected local Ollama vision models.
- Streaming chat endpoint and frontend partial-response rendering.
- Optional CPU-friendly live Ollama smoke tests.
- Docker Compose deployment, test Compose services, GitHub Actions CI, and
  release-readiness documentation.

### Security

- Local credential file with salted PBKDF2 password hashes.
- HttpOnly session cookies for account controls.
- Bearer API-key protection for AI and repository endpoints.
- Ignored local secret/config/data files and repository hygiene tests.
- Trusted-network deployment guidance and backup/restore documentation.

### Known Limitations

- The default deployment remains trusted-network first and is not a public
  multi-tenant service.
- Browser chat history is stored in localStorage on the current device.
- Login sessions are in memory and end when the backend restarts.
- External vector database backends beyond JSON are still early adapter work.
- Broad OCR workflows, semantic memory, and repository lifecycle automation are
  still planned for future releases.
