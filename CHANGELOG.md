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

### Release Candidate Checklist

- [x] README landing page reviewed and refreshed for public preview wording.
- [x] Setup docs aligned with the JSON default and optional Chroma adapter.
- [x] Example configuration files reviewed for placeholders, empty secrets, and
  trusted-network defaults.
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
