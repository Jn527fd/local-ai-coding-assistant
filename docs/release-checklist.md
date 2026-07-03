# Release Checklist

Use this checklist for every public release candidate. Do not release until all
required items are complete or explicitly deferred with rationale.

## 1. Scope

- [ ] Confirm the release branch and target version.
- [ ] Confirm no unfinished phase work is included accidentally.
- [ ] Review `CHANGELOG.md` and update the release date.
- [ ] Review `README.md` feature and limitation claims.
- [ ] Confirm `docs/development-roadmap.md` and `roadmap_v2.md` describe the
  next work accurately.

## 2. Local Configuration Hygiene

- [ ] `git status --short` contains only intentional source/docs/test changes.
- [ ] `git ls-files -ci --exclude-standard` returns no tracked ignored files.
- [ ] `.env`, `backend/.env`, `frontend/.env`, credentials, app settings,
  uploads, and generated indexes are not tracked.
- [ ] Example config files still contain safe placeholder values.

## 3. Security and Deployment Review

- [ ] Read `SECURITY.md`.
- [ ] Read `docs/deployment-hardening.md`.
- [ ] Confirm no docs claim the app is public-internet hardened.
- [ ] Confirm reverse proxy and HTTPS requirements are documented for
  untrusted networks.
- [ ] Confirm `SESSION_COOKIE_SECURE` guidance matches the deployment mode.
- [ ] Confirm Ollama is not exposed directly.

## 4. Backup and Restore

- [ ] Read `docs/backup-restore.md`.
- [ ] Create a backup of local data before deployment changes.
- [ ] Confirm restore instructions were tested or manually reviewed for the
  target environment.
- [ ] Rotate credentials and API keys when restoring to a different machine.

## 5. Dependency Review

- [ ] Read `docs/dependency-security.md`.
- [ ] Review Python requirement changes.
- [ ] Review frontend package and lockfile changes.
- [ ] Review Dockerfile and Compose changes.
- [ ] Run optional audit tooling where available and record findings.

## 6. Required Tests

- [ ] Backend tests: `.venv\Scripts\python.exe -m pytest` or
  `python -m pytest`.
- [ ] Frontend lint: `node scripts/lint-check.mjs` from `frontend/`.
- [ ] Frontend unit/integration tests: `node node_modules/vitest/vitest.mjs run`
  or `npm run test:run`.
- [ ] Frontend production build: `npm run build`.
- [ ] Whitespace check: `git diff --check`.

## 7. Docker Verification

- [ ] `docker compose -f docker-compose.test.yml run --rm backend-test`
- [ ] `docker compose -f docker-compose.test.yml run --rm frontend-test`
- [ ] `docker compose -f docker-compose.test.yml down --remove-orphans`
- [ ] `docker compose up --build --detach`
- [ ] `docker compose ps`
- [ ] `make smoke-docker`

## 8. Manual Smoke

- [ ] Sign in with a configured user.
- [ ] Save and verify an API key.
- [ ] Refresh local models/tools.
- [ ] Send a text chat and verify streaming output.
- [ ] Upload, process, index, and search a small text document.
- [ ] Run a RAG chat and verify sources.
- [ ] Verify settings are per-chat.
- [ ] Optional: run live Ollama smoke with `RUN_OLLAMA_TESTS=1`.

## 9. Release Record

- [ ] Add final commands and results to `docs/verification-log.md`.
- [ ] Tag the release only after tests and manual checks pass.
- [ ] Push the branch and tag.
- [ ] Keep a backup archive until the release has been verified after
  deployment.
