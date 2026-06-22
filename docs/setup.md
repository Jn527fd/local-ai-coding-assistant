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
2. Enter a private key. Short keys are accepted for local testing, but a
   longer private key is recommended for normal use.
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

Open the Account drawer to see eligible models installed in Ollama. The list
is generated dynamically from Ollama's local model metadata. Select
**Refresh local models** after pulling a model, or wait up to five seconds for
the open drawer to refresh automatically, then choose **Use installed model**.

The backend:

1. Reads models from Ollama's `/api/tags` endpoint
2. Parses each model's reported parameter size
3. Hides models above `MAX_MODEL_PARAMETERS_BILLION`
4. Rejects uninstalled, oversized, or unknown-size switch requests
5. Persists the selected installed model name as active

The application does not download models. Pull them directly with Ollama:

```bash
ollama pull qwen3:4b
ollama pull qwen2.5-coder:3b
ollama pull llama3.2:3b
ollama list
```

The application never deletes model files automatically. Remove one manually
only when desired with `ollama rm MODEL_NAME`.

## Manage Chats and Context

The Chat panel stores up to five chats per logged-in username in that browser.
Use **New** to create a chat. At five chats, the button is disabled until one
is deleted.

Each chat has separate model context. Select **Delete** beside a chat and
confirm to remove its messages from browser local storage. FastAPI never
stores chat history; it receives only the selected chat's recent context with
the current request. Switching models does not clear this browser history, so
the next active model receives the same selected-chat context. Deleted chats
cannot be included in later prompts. The backend also bounds the total prompt
size so a long saved chat does not make local inference progressively slower.

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
OLLAMA_NUM_PREDICT=768
OLLAMA_THINK=false
OLLAMA_KEEP_ALIVE=10m
CHAT_CONTEXT_MAX_CHARS=12000
DEFAULT_MODEL=qwen3:4b
MAX_MODEL_PARAMETERS_BILLION=7
DATA_DIRECTORY=../data
REPO_CHUNK_SIZE=2000
RAG_TOP_K=5
```

Login sessions are stored in memory and end when the backend restarts. Set
`SESSION_COOKIE_SECURE=true` only when the site is served over HTTPS.

`OLLAMA_THINK=false` keeps reasoning-capable models responsive for normal
chat. Increase `OLLAMA_NUM_PREDICT` only when longer answers are worth the
additional generation time. `CHAT_CONTEXT_MAX_CHARS` must be at least 12000.

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

By default, the production frontend uses `FRONTEND_API_BASE_URL=auto`. That
makes the browser call the backend on the same hostname or IP address used to
open the frontend. For a Linux host at `192.168.1.50`, open:

```text
http://192.168.1.50:5173
```

If `.env` already hardcodes a different `FRONTEND_API_BASE_URL`, reset it:

```dotenv
FRONTEND_API_BASE_URL=auto
```

Then rebuild once:

```bash
docker compose up --build --detach
```

HTTP does not encrypt passwords, cookies, or API keys; use an HTTPS reverse
proxy before accessing the app across an untrusted network.

## Tests

Docker and Ollama may remain running because tests use isolated temporary
files and a fake model service:

```bash
source .venv/bin/activate
python -m pytest

cd frontend
npm test
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

Use `ollama list` to verify the model is stored locally. Confirm that its
reported parameter size is 7B or smaller, then select **Refresh local models**
in the Account drawer.

### Port already in use

```bash
ss -ltnp | grep -E ':8000|:5173'
```

Stop the previous local process or run `docker compose down`.
