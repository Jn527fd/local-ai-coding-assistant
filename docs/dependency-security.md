# Dependency and Security Review

This project intentionally keeps default tests hermetic and Ollama-free. The
dependency review process should preserve that property.

## Dependency Sources

Python:

- `requirements.txt`
- `requirements-dev.txt`
- `backend/requirements.txt`
- `backend/requirements-dev.txt`
- `constraints.txt`

Frontend:

- `frontend/package.json`
- `frontend/pnpm-lock.yaml`
- `frontend/package.json`
- `frontend/package-lock.json`

Containers:

- `backend/Dockerfile`
- `backend/Dockerfile.test`
- `frontend/Dockerfile`
- `frontend/Dockerfile.test`
- `docker-compose.yml`
- `docker-compose.test.yml`

## Review Cadence

Before each public release candidate:

1. Review dependency diffs in the files above.
2. Reinstall from lock/requirements files in a clean environment.
3. Run default backend and frontend tests.
4. Run Docker test images.
5. Run optional live Ollama smoke tests only on a machine prepared for them.
6. Record results in `docs/verification-log.md`.

## Useful Audit Commands

These tools are optional and may require installation:

```bash
python -m pip install pip-audit
python -m pip_audit -r requirements.txt -r backend/requirements.txt

cd frontend
pnpm audit --prod
pnpm audit
```

Treat audit results as inputs for review, not as automatic proof that the app
is safe. Document accepted risk for any unresolved finding.

## Update Rules

- Prefer small dependency update pull requests.
- Keep backend and frontend updates separate when practical.
- Do not update generated lockfiles without the matching manifest change.
- Do not introduce network access into default tests.
- Keep live Ollama tests opt-in with `RUN_OLLAMA_TESTS=1`.
- Rebuild Docker test images after dependency changes.

## Secret and Artifact Hygiene

Before pushing:

```bash
git status --short
git ls-files -ci --exclude-standard
git diff --check
```

No local credentials, app settings, uploaded files, generated indexes, virtual
environments, dependency folders, build output, or model files should be
tracked.
