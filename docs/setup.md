# Linux Mint Setup Guide

## Prerequisites

- Linux Mint and a working NVIDIA driver
- Python 3.10+ with `venv`
- Node.js `20.19+` or `22.12+` with npm
- Docker Engine with the Compose plugin
- Ollama
- Git and curl

Verify:

```bash
nvidia-smi
python3 --version
node --version
npm --version
docker compose version
```

## Prepare Ollama

Follow the [official Ollama Linux guide](https://docs.ollama.com/linux), then:

```bash
sudo systemctl enable --now ollama
ollama pull qwen3:4b
curl http://127.0.0.1:11434/api/tags
```

The application manages later model downloads through Ollama. It never writes
directly into Ollama's model directory.

## Project Setup

```bash
cd ~/local-ai-coding-assistant
bash scripts/setup.sh
```

The script creates `.venv`, installs backend/frontend dependencies, creates
local `.env` files, and copies safe templates into `data/config/` without
overwriting existing local settings.

## Create Login Credentials

Add a local user:

```bash
.venv/bin/python scripts/manage_credentials.py set YOUR_USERNAME
```

Enter and confirm a password of at least eight characters. The script writes:

```text
data/config/credentials.json
```

The file is ordinary editable JSON:

```json
{
  "users": [
    {
      "username": "YOUR_USERNAME",
      "password_hash": "pbkdf2_sha256$..."
    }
  ]
}
```

Do not replace `password_hash` with a plaintext password. Use the management
script to generate or update hashes:

```bash
.venv/bin/python scripts/manage_credentials.py list
.venv/bin/python scripts/manage_credentials.py set ANOTHER_USER
.venv/bin/python scripts/manage_credentials.py remove OLD_USER
```

The backend rereads this file on each login, so username entries may be
reviewed manually without restarting.

## Start Locally

```bash
bash scripts/start.sh
```

Open `http://localhost:5173` and sign in. The start script runs FastAPI on
port `8000` and Vite on `5173`; `Ctrl+C` stops both.

## Add and Verify the API Key

After login:

1. Select the circular account avatar in the top-right.
2. Enter a private key containing at least 16 characters.
3. Select **Save key**.
4. Select **Check connection**.

The key is stored in two local places:

- Browser local storage, so the UI remembers it between sessions
- `data/config/app-settings.json`, so FastAPI knows the active key

The UI never displays the saved backend key. The Account status says
**Connected** only when the browser key matches the active backend value.

For programmatic setup, `API_KEY` in `backend/.env` remains a fallback. A key
saved through the Account UI overrides that fallback.

## Switch Models

Open the Account drawer and select an approved model:

```text
qwen3:4b
qwen2.5-coder:3b
qwen2.5-coder:7b
llama3.2:1b
llama3.2:3b
```

Select **Install and activate** and confirm the cleanup warning. The UI shows
each operation phase and download progress.

The backend:

1. Rejects anything outside the server allowlist
2. Unloads the current model from memory
3. Downloads the selected model through Ollama's streaming pull API
4. Persists it as the active model
5. Deletes the previous model through Ollama after the new pull succeeds

The old installation is preserved when a download fails. Set
`DELETE_PREVIOUS_MODEL=false` in `backend/.env` to keep old models.

Model switching requires internet access to download a model that is not
already installed. Chat prompts and repository content still remain local.

## Manage Chats and Context

The Chat panel stores up to five chats per logged-in username in that browser.
Use **New** to create a chat. At five chats, the button is disabled until one
is deleted.

Each chat has separate model context. Select **Delete** beside a chat and
confirm to remove its messages from browser local storage. FastAPI never
stores chat history; it receives only the selected chat's recent context with
the current request. Deleted chats therefore cannot be included in later
prompts.

Browser storage is application-local persistence, not guaranteed forensic
disk erasure. Clear site data in the browser when decommissioning a device.

## Local Configuration Files

`backend/.env` includes:

```dotenv
API_KEY=
CREDENTIALS_FILE=../data/config/credentials.json
LOCAL_SETTINGS_FILE=../data/config/app-settings.json
SESSION_COOKIE_NAME=local_ai_session
SESSION_TTL_HOURS=12
SESSION_COOKIE_SECURE=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_TIMEOUT_SECONDS=120
MODEL_PULL_TIMEOUT_SECONDS=3600
DELETE_PREVIOUS_MODEL=true
DEFAULT_MODEL=qwen3:4b
DATA_DIRECTORY=../data
REPO_CHUNK_SIZE=2000
RAG_TOP_K=5
```

Login sessions are stored in memory and end when the backend restarts. Set
`SESSION_COOKIE_SECURE=true` only when the site is served over HTTPS.

## Files Intentionally Ignored by Git

Real secrets and mutable local values are excluded:

```text
.env
backend/.env
frontend/.env
data/config/credentials.json
data/config/app-settings.json
```

These safe templates are committed:

```text
.env.example
backend/.env.example
frontend/.env.example
credentials.example.json
app-settings.example.json
```

Before pushing, verify:

```bash
git status --short
git check-ignore data/config/credentials.json
git check-ignore data/config/app-settings.json
```

## Docker Compose

Prepare local files before starting containers:

```bash
cd ~/local-ai-coding-assistant
cp .env.example .env
test -f backend/.env || cp backend/.env.example backend/.env
mkdir -p data/config
test -f data/config/credentials.json || \
  cp credentials.example.json data/config/credentials.json
test -f data/config/app-settings.json || \
  cp app-settings.example.json data/config/app-settings.json
python3 scripts/manage_credentials.py set YOUR_USERNAME
sed -i "s/^APP_UID=.*/APP_UID=$(id -u)/" .env
docker compose up --build --detach
docker compose ps
```

`./data` is mounted at `/app/data`, so credentials, API settings, the active
model name, and repository indexes persist across container replacement.
Ollama continues running on the Linux host at `127.0.0.1:11434`.

## Home-Network Access

For a Linux host at `192.168.1.50`, set in the root `.env`:

```dotenv
FRONTEND_API_BASE_URL=http://192.168.1.50:8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.1.50:5173
```

Then rebuild:

```bash
docker compose up --build --detach
```

Open `http://192.168.1.50:5173` from a trusted LAN device. HTTP does not
encrypt passwords, cookies, or API keys; use an HTTPS reverse proxy before
accessing the app across an untrusted network.

## Tests

Docker and Ollama may remain running because tests use isolated temporary
files and a fake model service:

```bash
source .venv/bin/activate
python -m pytest
```

## Troubleshooting

### Login says credentials are not configured

```bash
ls -l data/config/credentials.json
.venv/bin/python scripts/manage_credentials.py list
```

### API key says not connected

Open Account, save the key again, then check connection. The browser copy must
match `data/config/app-settings.json` or the `API_KEY` environment fallback.

### Model switch fails

```bash
systemctl status ollama
curl http://127.0.0.1:11434/api/tags
docker compose logs backend
df -h
```

Confirm internet access and enough disk space for the selected download.

### Port already in use

```bash
ss -ltnp | grep -E ':8000|:5173'
```

Stop the previous local process or run `docker compose down`.
