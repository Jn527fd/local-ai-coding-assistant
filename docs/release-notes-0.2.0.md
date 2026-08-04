# Release Notes: 0.2.0 Stable v2

Date prepared: 2026-07-05

Status: stable release notes prepared; release tag deferred in this environment.

This release stabilizes the Roadmap v2 work after `0.1.0`. The app remains a
local, self-hosted AI coding assistant for one operator or a trusted network.
It is not a public multi-tenant service.

## Highlights

- Optional backend conversation persistence with browser localStorage fallback,
  import/export, deletion semantics, and SQLite metadata mirroring.
- Durable local SQLite metadata store with conservative migrations.
- Local document/indexing jobs with progress/status APIs and conservative
  cancellation.
- Document ingestion v2 for TXT, Markdown, PDF, DOCX, HTML, CSV, and TSV,
  including file sniffing, diagnostics, and duplicate detection.
- Qdrant is the standard vector database, with Docker Compose persistence,
  stronger adapter diagnostics, and export/import utilities.
- Deterministic retrieval evaluation fixtures and source metadata regression
  checks.
- Opt-in repository vector indexing, freshness warnings, and language-aware
  source chunk metadata while preserving legacy keyword repository RAG.
- Frontend state extraction, accessibility/mobile polish, and diagnostics UI.
- Trusted-network security hardening: CSRF checks, optional signed sessions,
  login rate limiting, security headers, redacted audit logs, and API-key
  rotation UX.
- Metadata-only diagnostics and redacted support-bundle export.
- Production Compose template, environment validation, and backup-before-upgrade
  helper.

## Known Limitations

- The app is designed for localhost or trusted-network use. Do not expose the
  frontend, backend, or Ollama directly to the public internet.
- Browser-local chats remain browser-local unless explicitly migrated or stored
  with backend persistence.
- Login sessions are in memory unless a persistent session signing key is
  configured, and active sessions still end when backend state is restarted.
- Qdrant is the standard vector database. Docker Compose includes a persistent
  Qdrant volume; JSON vector storage remains only as an internal fallback when
  Qdrant client support is unavailable.
- OCR and vision workflows depend on locally installed optional tools/models.
- Context management is automatic. Older `contextCompressor` settings are
  accepted for compatibility but are no longer user-selectable.
- Live Ollama smoke tests validate wiring only, not answer quality.

## Release Blockers in This Environment

Do not create the stable tag from this sandbox until these checks are completed
on the target release machine:

- Frontend Vitest, blocked here by sandbox config-read restrictions.
- Docker/Compose validation, blocked here by sandbox access to local Docker
  config.
- Production env validation with real local `.env`, `backend/.env`, and
  credentials.
- Manual browser smoke and optional live Ollama smoke.

## Required Pre-Tag Checks

- Full backend pytest passes.
- Frontend lint, Vitest, and production build pass.
- Deployment script tests and `git diff --check` pass.
- `python3 scripts/validate_env.py` passes or all warnings are documented for
  the target machine.
- `docker compose -f docker-compose.prod.yml config` succeeds on the target
  machine.
- Backup/restore, diagnostics, security/trust-boundary, and upgrade docs are
  reviewed.
