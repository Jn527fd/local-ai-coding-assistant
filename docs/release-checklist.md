# Release Checklist

Use this checklist for every public release candidate. Do not release until all
required items are complete or explicitly deferred with rationale.

## Current RC Review: 2026-07-04

Completed in the current environment:

- [x] Scope frozen for Roadmap v2 Phase 15.
- [x] README, API, setup, backup/restore, deployment hardening, security, and
  release docs reviewed for current claims.
- [x] `CHANGELOG.md` updated with RC QA status.
- [x] `docs/release-notes-0.2.0-rc1.md` drafted.
- [x] Backend tests passed: `163 passed, 7 skipped`.
- [x] Frontend lint and production build passed.
- [x] Deployment script tests passed.
- [x] Compile and whitespace checks passed.
- [x] Screenshot references under `docs/assets/` exist.

Deferred or blocked:

- [ ] Frontend Vitest: blocked by sandbox config-read restrictions in this
  environment.
- [ ] Docker/Compose validation: blocked by sandbox denial reading local Docker
  config.
- [ ] Production env validation on this checkout: blocked by intentionally
  missing local `.env`, `backend/.env`, and credentials.
- [ ] Manual browser smoke and optional live Ollama smoke: not run in this
  environment.
- [ ] Release tag: not created; complete deferred checks first.

## Stable v2 Review: 2026-07-05

Completed in the current environment:

- [x] Phase 15 RC verification log, release checklist, changelog, README,
  setup, deployment hardening, security, and backup docs reviewed.
- [x] Stable v2 release notes prepared in `docs/release-notes-0.2.0.md`.
- [x] Support and hotfix guidance added in `docs/support.md`.
- [x] Critical/high blockers from this environment are documented rather than
  hidden.

Deferred or blocked before tagging:

- [ ] Frontend Vitest on a non-sandboxed machine.
- [ ] Docker/Compose validation on a machine with readable Docker config.
- [ ] Production env validation on the target machine with real local secrets.
- [ ] Manual browser smoke and optional live Ollama smoke.
- [ ] Stable release tag; not created from this sandbox.

## 1. Scope

- [ ] Confirm the release branch and target version.
- [ ] Confirm no unfinished phase work is included accidentally.
- [ ] Review `CHANGELOG.md` and update the release date.
- [ ] Review `README.md` feature and limitation claims.
- [ ] Confirm `docs/development-roadmap.md` describes the
  next work accurately.

## 2. Local Configuration Hygiene

- [ ] `git status --short` contains only intentional source/docs/test changes.
- [ ] `git ls-files -ci --exclude-standard` returns no tracked ignored files.
- [ ] `.env`, `backend/.env`, `frontend/.env`, credentials, app settings,
  uploads, and generated indexes are not tracked.
- [ ] Example config files still contain safe placeholder values.
- [ ] `python3 scripts/validate_env.py` has been run for the target deploy
  machine, or warnings are documented.

## 3. Security and Deployment Review

- [ ] Read `SECURITY.md`.
- [ ] Read `docs/deployment-hardening.md`.
- [ ] Confirm no docs claim the app is public-internet hardened.
- [ ] Confirm reverse proxy and HTTPS requirements are documented for
  untrusted networks.
- [ ] Confirm `SESSION_COOKIE_SECURE` guidance matches the deployment mode.
- [ ] Confirm Ollama is not exposed directly.
- [ ] Confirm `docker-compose.prod.yml` does not publish Ollama or backend API
  ports publicly by default.

## 4. Backup and Restore

- [ ] Read `docs/backup-restore.md`.
- [ ] Create a backup of local data before deployment changes.
- [ ] For container replacement, run `python3 scripts/upgrade.py` and keep the
  generated `backups/pre-upgrade-data-*.zip` archive until verification passes.
- [ ] Confirm restore instructions were tested or manually reviewed for the
  target environment.
- [ ] Rotate credentials and optional legacy API keys when restoring to a
  different machine.

## 5. Dependency Review

- [ ] Read `docs/dependency-security.md`.
- [ ] Review Python requirement changes.
- [ ] Review frontend package and lockfile changes.
- [ ] Review Dockerfile and Compose changes.
- [ ] Run optional audit tooling where available and record findings.

## 6. Required Tests

- [x] Backend tests: `.venv\Scripts\python.exe -m pytest` or
  `python -m pytest`.
- [x] Frontend format: `pnpm format:check` from `frontend/`.
- [x] Frontend lint: `pnpm lint` from `frontend/`.
- [x] Frontend typecheck: `pnpm typecheck` from `frontend/`.
- [x] Frontend unit/integration tests: `pnpm test` from `frontend/`.
- [x] Frontend production build: `pnpm build` from `frontend/`.
- [x] Frontend e2e tests: `pnpm test:e2e` from `frontend/`.
- [x] Whitespace check: `git diff --check`.
- [ ] Env validation script tests: `python -m pytest tests/test_deployment_scripts.py`.

## 7. Docker Verification

- [x] `docker compose -f docker-compose.test.yml run --rm backend-test`
- [x] `docker compose -f docker-compose.test.yml run --rm frontend-test`
- [x] `docker compose -f docker-compose.test.yml down --remove-orphans`
- [x] `docker compose -f docker-compose.prod.yml config`
- [ ] `docker compose up --build --detach`
- [ ] `docker compose ps`
- [ ] `make smoke-docker`

## 8. Manual Smoke

- [ ] Sign in with a configured user.
- [ ] Optional: save and verify an API key if legacy scripts/manual API calls
  are part of the release smoke.
- [ ] Refresh local models/tools.
- [ ] Send a text chat and verify streaming output.
- [ ] Upload, process, index, and search a small text document.
- [ ] Run a RAG chat and verify sources.
- [ ] Verify settings are per-chat.
- [ ] Optional: run live Ollama smoke with `RUN_OLLAMA_TESTS=1`.

## 9. Release Record

- [ ] Add final commands and results to `docs/verification-log.md`.
- [ ] Confirm screenshot references in `README.md` and `docs/assets/` render.
- [ ] Confirm generated docs, screenshots, and support bundles do not contain
  secrets, prompts, private paths, uploaded contents, or local vector data.
- [ ] Tag the release only after tests and manual checks pass.
- [ ] Push the branch and tag.
- [ ] Keep a backup archive until the release has been verified after
  deployment.
