# Security Policy

## Supported Scope

This project is designed for a single operator or trusted home/lab network. It
is not currently a hardened public internet, multi-tenant, or enterprise access
control system.

The supported release target is the current `main` branch and tagged release
candidates produced from it. Older development branches may contain incomplete
security behavior and should not be treated as maintained deployments.

## Trust Model

Expected deployment:

- The backend, frontend, data directory, and Ollama daemon run on hardware the
  operator controls.
- Users access the app from the same machine or a trusted LAN.
- The operator controls local credentials, the Bearer API key, Docker mounts,
  pulled Ollama models, and uploaded documents.

Do not expose the FastAPI backend, frontend development server, or Ollama
daemon directly to the public internet. Use a reverse proxy with HTTPS and
additional access controls before accessing the app across an untrusted
network.

Current local controls include HttpOnly SameSite session cookies, CSRF checks
for unsafe cookie-authenticated requests, optional persistent session signing,
in-memory login rate limiting, security response headers, redacted audit logs
for auth/settings changes, and Bearer-key protection for AI/data endpoints.
These controls improve trusted-network safety but do not make the app a public
multi-tenant service.

## Sensitive Data

The following files and directories can contain private data and must remain
outside source control:

- `.env`
- `backend/.env`
- `frontend/.env`
- `data/config/credentials.json`
- `data/config/app-settings.json`
- `data/uploads/`
- `data/vector_indexes/`
- `data/indexes/`
- local repository mounts

## Reporting Security Issues

Do not publish secrets, API keys, uploaded files, prompts, generated indexes,
or private source code in a public issue.

If the repository hosting platform provides private vulnerability reporting,
use that first. Otherwise, open a minimal issue describing the affected area
without sensitive data and ask for a private disclosure channel.

## Before Broader Deployment

Review and complete:

- [Deployment hardening](docs/deployment-hardening.md)
- [Backup and restore](docs/backup-restore.md)
- [Dependency and security review](docs/dependency-security.md)
- [Release checklist](docs/release-checklist.md)
