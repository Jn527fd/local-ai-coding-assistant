# Backup and Restore

Backups protect local credentials, app settings, uploaded documents, generated
indexes, and vector data. They do not capture browser-local chat history unless
you export or back up the browser profile separately.

## Data to Back Up

Back up the repository plus these mutable local paths:

```text
.env
backend/.env
frontend/.env
data/config/credentials.json
data/config/app-settings.json
data/uploads/
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
  -czf local-ai-coding-assistant-backup-YYYYMMDD.tar.gz \
  .env backend/.env frontend/.env data
```

Store the archive somewhere encrypted if it contains credentials, API keys,
uploaded documents, or private source-derived indexes.

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

Then sign in, verify the API key status, refresh local models/tools, and run a
small chat plus document search.

## Rotation After Restore

Rotate credentials when moving data to a new machine:

- Reset local user passwords with `scripts/manage_credentials.py`.
- Replace the Bearer API key in the UI or `data/config/app-settings.json`.
- Rebuild containers if environment variables changed.
- Confirm ignored files are still ignored with `git status --short`.

## Browser Chat History

Conversations live in browser localStorage. They are not included in backend
data backups. Treat browser profile backup, export, or future server-side chat
persistence as separate work.
