# Deployment Hardening

This guide documents the safer self-hosted deployment posture for the current
release. It does not turn the app into a public multi-tenant service.

## Supported Exposure

Recommended:

- Localhost development on one machine.
- Docker Compose on one trusted host.
- Access from trusted devices on the same private LAN.
- Optional HTTPS reverse proxy for access across an untrusted network.

Avoid:

- Exposing `5173`, `8000`, or `11434` directly to the public internet.
- Publishing Ollama to a routable address.
- Reusing a weak API key or default example credentials.
- Mounting private repositories with write access when read-only access is
  enough.

## Network Layout

Keep Ollama bound to the host or private interface only. The backend should be
the only service that talks to Ollama.

For Docker Compose, keep the default model:

- Browser reaches the frontend.
- Browser sends API requests to the backend.
- Backend reaches host Ollama at `127.0.0.1:11434` through host networking.
- `./data` is the only persistent mutable application state mounted into the
  backend.

## HTTPS Reverse Proxy

Use HTTPS before sending passwords, cookies, or Bearer API keys across an
untrusted network.

Recommended proxy behavior:

- Terminate TLS with a valid certificate.
- Redirect HTTP to HTTPS.
- Forward `/` to the frontend service.
- Forward backend API paths to FastAPI.
- Preserve `Host`, `X-Forwarded-Proto`, and `X-Forwarded-For`.
- Add a request body size limit that matches or is lower than
  `DOCUMENT_MAX_UPLOAD_BYTES`.
- Add upstream timeouts long enough for local model generation.
- Do not proxy Ollama directly.
- Keep or add security response headers. The backend already sets
  `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`,
  `Referrer-Policy: no-referrer`, and a restrictive `Permissions-Policy`.

Example path groups for a reverse proxy:

```text
/auth/*
/account/*
/models/*
/components/*
/chat*
/documents/*
/repos/*
/health
/docs
/openapi.json
```

Everything else can route to the frontend.

## Cookie and API-Key Settings

Set `SESSION_COOKIE_SECURE=true` only when the app is served over HTTPS. Keep
it `false` for plain local HTTP development, or browsers will not send the
session cookie.

Set `SESSION_SIGNING_KEY` to a long random local secret when you want browser
sessions to survive backend restarts. If the key changes, existing sessions are
invalidated. Unsafe session-cookie requests require the readable CSRF cookie to
match the `X-CSRF-Token` header; the bundled frontend sends this automatically.

Login attempts are rate-limited in memory by username and client address.
Adjust `LOGIN_RATE_LIMIT_ATTEMPTS`, `LOGIN_RATE_LIMIT_WINDOW_SECONDS`, and
`LOGIN_LOCKOUT_SECONDS` only if trusted local users are being locked out during
normal use.

Use a strong Bearer API key for normal use. Rotate it before a public demo,
after screen sharing, and after copying local configuration between machines.
The Settings panel can generate a replacement local API key, but the user must
still press **Save key** to activate it.

Auth and API-key changes emit redacted audit log events. These logs include
action, username, client, and success/failure state, but not passwords or API
key values.

## Host and Container Controls

Before release or demo:

- Replace example credentials with real local users.
- Verify `data/config/credentials.json` and
  `data/config/app-settings.json` are ignored by Git.
- Keep repository mounts read-only where possible.
- Keep Docker images rebuilt from committed dependency files.
- Keep host firewall rules limited to the intended frontend/proxy ports.
- Keep Ollama and model files on trusted storage.

## Operational Smoke Check

After deployment:

```bash
docker compose ps
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:11434/api/tags
make smoke-docker
```

Then sign in through the browser, save an API key, verify capabilities, send a
short chat, and upload/process a small text document.
