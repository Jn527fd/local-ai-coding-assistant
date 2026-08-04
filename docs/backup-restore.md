# Backup and Restore

Backups protect local credentials, app settings, the SQLite metadata
catalogue, uploaded documents, generated indexes, vector data, and optional
backend-persisted conversations. They do not capture browser-local-only chat
history unless you export or back up the browser profile separately.

## Data to Back Up

Back up the repository plus these mutable local paths:

```text
.env
backend/.env
frontend/.env
data/config/credentials.json
data/config/app-settings.json
data/metadata/
data/uploads/
data/conversations/
data/vector_indexes/
data/indexes/
data/repos/
```

If repositories are mounted outside this project, back them up separately.
Ollama model files are managed by Ollama and can usually be re-pulled, but a
full machine backup may include them if download time matters.

## Create a Backup

Stop writes first:

```bash
docker compose down
```

Create an archive from the project root:

```bash
tar --exclude=.git \
  --exclude=.venv \
  --exclude=frontend/node_modules \
  --exclude=frontend/dist \
  --exclude=frontend/node_modules \
  --exclude=frontend/dist \
  -czf local-ai-coding-assistant-backup-YYYYMMDD.tar.gz \
  .env backend/.env frontend/.env data
```

Store the archive somewhere encrypted if it contains credentials, API keys,
uploaded documents, or private source-derived indexes.

For container upgrades, the scripted helper creates a `data/` zip backup before
replacing services:

```bash
python3 scripts/upgrade.py
```

Re-run with `--apply` only after reviewing validation warnings:

```bash
python3 scripts/upgrade.py --apply
```

## Restore

On the target machine:

```bash
git clone YOUR_REPOSITORY_URL local-ai-coding-assistant
cd local-ai-coding-assistant
tar -xzf /path/to/local-ai-coding-assistant-backup-YYYYMMDD.tar.gz
docker compose up --build --detach
docker compose ps
```

Verify:

```bash
curl http://127.0.0.1:8000/health
docker compose logs backend --tail=100
```

Then sign in, refresh local models/tools, and run a small chat plus document
search. Verify the optional API-key status only if you use legacy scripts or
manual API calls.

Check the metadata database after restore:

```bash
cd backend
../.venv/bin/python -m app.metadata.cli status
../.venv/bin/python -m app.metadata.cli migrate
```

The migration command is conservative: it initializes a missing database,
imports existing JSON metadata where practical, and leaves original artifacts
unchanged. If it reports a corrupt or unsupported database, stop and restore
from a known-good backup before continuing.

## Rotation After Restore

Rotate credentials when moving data to a new machine:

- Reset local user passwords with `scripts/manage_credentials.py`.
- Replace the optional Bearer API key in the UI or
  `data/config/app-settings.json` if you use legacy scripts or manual API
  calls.
- Rebuild containers if environment variables changed.
- Confirm ignored files are still ignored with `git status --short`.

## Browser Chat History

Browser-local conversations live in browser localStorage. They are not included
in backend data backups unless you first migrate them to backend storage from
Settings.

Backend-persisted conversations live under `data/conversations/` and are
included when the `data/` directory is backed up. Restoring that directory
restores the backend conversation store for the same local usernames.

The SQLite metadata catalogue lives under `data/metadata/`. It can be restored
with the rest of `data/`, or regenerated from the JSON metadata artifacts by
running the migration command if the database file is missing.
