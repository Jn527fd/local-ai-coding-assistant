# Frontend

This is the production React/Vite frontend for Local AI Coding Assistant. It
uses typed service contracts so the app can run against the real FastAPI
backend in HTTP mode while keeping deterministic mocks for tests.

## Toolchain

- Node.js 22.x
- pnpm 11.x

## Local Development

From the repository root:

```bash
make install-frontend
make run-frontend
```

Or from this folder:

```bash
pnpm install --frozen-lockfile
pnpm dev
```

The Docker Compose frontend runs through Nginx and proxies `/api/*` requests to
the backend container.

## Environment

Copy `.env.example` to `.env.local` for local Vite development.

| Variable | Purpose |
| --- | --- |
| `VITE_API_BASE_URL` | Backend API base path. Use `/api` when the frontend proxy is active. |
| `VITE_USE_MOCK_API` | Set to `false` for the real backend or `true` for deterministic mocks. |
| `PORT` | Vite dev server port. |

Only `VITE_` variables are exposed to browser code. Do not put secrets in
frontend environment files.

## Checks

```bash
pnpm lint
pnpm typecheck
pnpm test
pnpm build
```

Root Make targets run the same checks:

```bash
make test-frontend
```
