# API Reference

## Base URL

The default backend is `http://localhost:8000`. Interactive OpenAPI
documentation is available at `/docs`.

## Authentication Layers

The app uses two local authentication mechanisms:

1. **Login session cookie:** `/auth/login` verifies
   `data/config/credentials.json` and sets an HttpOnly cookie. Account and
   model-management endpoints require this cookie.
2. **Bearer API key:** `/chat` and `/repos/*` require
   `Authorization: Bearer <API_KEY>`. The active key comes from the ignored
   local app-settings file, with the `API_KEY` environment variable as a
   fallback.

`GET /` and `GET /health` remain public.

## Endpoint Summary

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/` | None | Application metadata |
| `GET` | `/health` | None | Backend process health |
| `POST` | `/auth/login` | None | Create local browser session |
| `GET` | `/auth/me` | Session | Return signed-in user |
| `POST` | `/auth/logout` | None | Revoke current session |
| `GET` | `/account/status` | Session | Check API-key state |
| `PUT` | `/account/api-key` | Session | Persist a new API key |
| `GET` | `/models/status` | Session | Model catalog and operation state |
| `POST` | `/models/switch` | Session | Install and activate a model |
| `POST` | `/chat` | Bearer key | Chat with the active model |
| `POST` | `/repos/index-local` | Bearer key | Index a local directory |
| `POST` | `/repos/ask` | Bearer key | Ask the active model about an index |

## Public Endpoints

```bash
curl http://localhost:8000/
curl http://localhost:8000/health
```

`GET /health` returns:

```json
{"status":"ok"}
```

It confirms FastAPI is running; it does not verify Ollama.

## Login Session

Use a cookie jar for command-line testing:

```bash
curl -c session.cookies -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"YOUR_USERNAME","password":"YOUR_PASSWORD"}'
```

Successful response:

```json
{"username":"YOUR_USERNAME"}
```

Check or end the session:

```bash
curl -b session.cookies http://localhost:8000/auth/me
curl -b session.cookies -X POST http://localhost:8000/auth/logout
```

Invalid credentials return `401`. A missing or malformed credentials file
returns `503` with a local setup message.

## Account API Key

Save a key of at least 16 characters:

```bash
curl -b session.cookies -X PUT http://localhost:8000/account/api-key \
  -H "Content-Type: application/json" \
  -d '{"api_key":"your-private-api-key"}'
```

The response never includes the secret:

```json
{
  "username": "YOUR_USERNAME",
  "api_key_configured": true,
  "api_key_active": true
}
```

Check whether a candidate key matches the active key:

```bash
curl -b session.cookies http://localhost:8000/account/status \
  -H "Authorization: Bearer your-private-api-key"
```

The backend persists the active key in
`data/config/app-settings.json`. The React frontend also stores the user's
entered copy in browser local storage.

## Model Status and Switching

Get the approved catalog, installed model names, Ollama connectivity, active
model, and current operation state:

```bash
curl -b session.cookies http://localhost:8000/models/status
```

Start a switch:

```bash
curl -b session.cookies -X POST http://localhost:8000/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:7b"}'
```

The request returns `202`; poll `/models/status` for:

```text
unloading -> downloading -> activating -> cleaning -> complete
```

The response includes `progress`, `message`, `error`, and `warning`. Only the
server allowlist is accepted:

```text
qwen3:4b
qwen2.5-coder:3b
qwen2.5-coder:7b
llama3.2:1b
llama3.2:3b
```

An unsupported model returns `400`; a second concurrent switch returns `409`.
Chat and repository generation return `409` while a switch is running.

The old model is unloaded first. The replacement is downloaded and made
active, then the old model is deleted when `DELETE_PREVIOUS_MODEL=true`.
Deletion happens after a successful pull to preserve the previous installation
when a download fails.

## Chat

Chat always uses the active model:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message":"Explain dependency injection briefly.",
    "history":[
      {"role":"user","content":"What is FastAPI?"},
      {"role":"assistant","content":"FastAPI is a Python web framework."}
    ]
  }'
```

Response:

```json
{
  "model": "qwen3:4b",
  "answer": "Generated text from the local model."
}
```

The optional legacy `model` request field is accepted only when it exactly
matches the active approved model. It cannot be used to bypass model switching.
`history` is optional, accepts at most 30 user/assistant messages, and is used
only to construct the current Ollama prompt. The backend does not persist it.

Common errors:

| Status | Meaning |
| --- | --- |
| `400` | Requested legacy model is unsupported |
| `401` | Bearer key is missing or invalid |
| `409` | Different model requested or switch in progress |
| `422` | Request validation failed |
| `502` | Ollama returned an invalid/error response |
| `503` | API key is unconfigured or Ollama is unavailable |
| `504` | Ollama timed out |

## Repository Indexing

```bash
SAMPLE_REPO_PATH="$(realpath sample-code-repository)"

curl -X POST http://localhost:8000/repos/index-local \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"path\":\"$SAMPLE_REPO_PATH\"}"
```

Docker uses `/repositories/...` paths. The response contains `repo_name`,
`indexed_files`, and `indexed_chunks`. Index files are stored beneath
`DATA_DIRECTORY/indexes`.

Supported extensions are `.py`, `.js`, `.jsx`, `.ts`, `.tsx`, `.md`, `.json`,
`.yaml`, `.yml`, `.html`, and `.css`. `.git`, `node_modules`, `.venv`,
`__pycache__`, `dist`, and `build` directories are ignored.

## Repository Questions

```bash
curl -X POST http://localhost:8000/repos/ask \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_name": "sample-code-repository",
    "question": "Where are the add and multiply functions implemented?"
  }'
```

Response:

```json
{
  "answer": "The functions are implemented in sample_app/calculator.py.",
  "sources": ["app.py", "sample_app/calculator.py"]
}
```

Repository answers use the same active model selected from the account panel.

## Security Notes

- Do not expose these endpoints directly to the public internet.
- Use HTTPS before sending cookies or Bearer keys across an untrusted network.
- The session cookie is HttpOnly and SameSite=Lax, but local HTTP is not
  encrypted.
- An authenticated Bearer caller can index paths readable by the backend.
- Model-management endpoints can download and delete local Ollama models and
  therefore require a valid login session.
