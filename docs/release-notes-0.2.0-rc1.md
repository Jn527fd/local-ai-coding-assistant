# Release Notes: 0.2.0-rc1

Date: 2026-07-04

This release candidate bundles the Roadmap v2 stabilization work completed
after `0.1.0`. It remains a trusted-network, self-hosted local AI assistant,
not a public multi-tenant service.

## Highlights

- Optional backend conversation persistence with import/export and browser
  localStorage fallback.
- SQLite metadata store and conservative migration layer.
- Background document/indexing jobs with progress metadata.
- Document ingestion v2 for TXT, Markdown, PDF, DOCX, HTML, CSV, and TSV.
- Vector adapter diagnostics, JSON export/import, and Chroma adapter coverage.
- Retrieval evaluation fixtures and regression checks.
- Opt-in repository vector indexing, freshness warnings, and language-aware
  source chunk metadata.
- Frontend state extraction, accessibility/mobile polish, and diagnostics UI.
- CSRF/session hardening, login rate limiting, security headers, redacted audit
  logs, and API-key rotation UX.
- Metadata-only diagnostics and redacted support bundle export.
- Production Compose template, environment validation, and backup-before-upgrade
  helper.

## Verification Summary

Passed in this environment:

- Full backend pytest: `163 passed, 7 skipped`.
- Targeted release/script/security diagnostics tests: `17 passed`.
- Frontend lint: passed for 46 files.
- Frontend production build: passed.
- Compile checks: passed.
- `git diff --check`: passed with expected Windows line-ending warnings.
- Screenshot references exist under `docs/assets/`.

Blocked or deferred in this environment:

- Frontend Vitest was blocked by sandbox config-read restrictions.
- Docker Compose validation was blocked by sandbox access to local Docker
  config.
- Production env validation correctly failed because local secrets and
  credentials are not present in this checkout.
- Manual browser smoke, live Ollama smoke, and release tagging were deferred.

## Tagging Status

Do not tag this release candidate from the current environment. Complete
frontend Vitest, Docker verification, production env validation on the target
machine, and manual smoke checks first.
