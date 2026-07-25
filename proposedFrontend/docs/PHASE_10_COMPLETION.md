# Phase 10 completion report

Date: July 19, 2026

## Status

Phase 10 backend-handoff documentation is complete.

Per the approval boundary for this phase, the separate final validation gate has not been executed and the required final implementation report has not been produced. The project is not being newly declared backend-ready by this phase report.

## Files added

- `README.md`
- `.env.example`
- `docs/backend-api.openapi.yaml`
- `docs/PHASE_10_COMPLETION.md`

## Files updated

- `docs/PHASE_9_COMPLETION.md` now records Phase 9 approval while leaving the final gate pending.

No application, service, route, test, build, or dependency file was changed during Phase 10.

## README handoff coverage

The project README now documents:

- Supported Node.js 22 and pnpm 11.9 toolchain versions.
- Lockfile installation and local Vite startup on Windows and Bash environments.
- Demo login and signup credentials.
- Browser-visible and process environment variables.
- Every public, protected, placeholder, deep-link, and fallback route.
- Application, feature, service, API-client, and domain boundaries.
- The four frontend service interfaces and central mutation policies.
- A concrete adapter sequence for replacing mocks with HTTP services.
- The important fact that `VITE_USE_MOCK_API` is reserved but not yet wired.
- Authentication, token, session restoration, OAuth, email verification, and password assumptions.
- Conversation-scoped prompt, model, source, and temporary settings behavior.
- Accepted, delta, complete, and failed streaming event expectations.
- Composer attachment, source upload, and local Modelfile limits.
- Error-envelope and HTTP-status expectations.
- Available validation commands and current CI behavior.
- Product and backend decisions that remain unresolved.

## Environment template

`.env.example` includes:

```dotenv
VITE_API_BASE_URL=http://localhost:3000/api
VITE_USE_MOCK_API=true
```

The template and README explicitly warn that `VITE_*` values are browser-visible and must never contain secrets. They also distinguish the active API base URL from the currently inactive mock-selection flag.

## OpenAPI draft

`docs/backend-api.openapi.yaml` is an OpenAPI 3.1 handoff proposal covering:

- Sign-in, sign-out, session restoration, email verification, account creation, and OAuth/SSO redirects.
- Conversation pagination, fetch, creation, rename, deletion, and conversation-scoped configuration.
- Non-streaming message submission and SSE message streaming.
- Message cancellation and retry.
- Proposed composer attachment upload.
- Source list, multipart upload, deletion, summary, and processing retry.
- Available model and pipeline-component discovery.

The draft includes typed schemas for sessions, users, conversations, messages, attachments, sources, model configuration, partial configuration updates, pagination, and error envelopes. It also provides request, success, validation, unauthorized, forbidden, conflict, rate-limit, file-size, media-type, not-found, and server-failure examples.

## Explicit backend assumptions and decisions

The documentation intentionally leaves these decisions to the backend, security, and product owners:

- Cookie sessions versus bearer-token storage and refresh rotation.
- SSE reconnection, resume tokens, replay behavior, and cancellation semantics.
- Multipart attachments versus presigned object-storage uploads.
- File scanning, parsing, storage, retention, and deletion guarantees.
- Temporary-conversation persistence and expiration.
- Optimistic concurrency/version fields.
- Canonical model identifiers, permissions, and fallback rules.
- OAuth/SSO callback, tenant, account-linking, and allowlist behavior.
- Password-reset delivery and token behavior for placeholder routes.

## Documentation checks performed

Phase 10 work was reviewed for the required README headings, route coverage, service-interface names, environment-variable disclosures, endpoint groups, model configuration schemas, error examples, and links between the README and OpenAPI draft.

No command from the final validation gate was run after the Phase 10 documentation changes. Specifically, this phase did not run the frozen install, format check, lint, type check, Vitest suite, Playwright suite, production build, keyboard walkthrough, screen-reader smoke test, accessibility scan, responsive walkthrough, network simulations, deep-link walkthrough, or browser-console check.

## Next gate

The next separately approved task is the final validation gate. Only after that gate passes should the required final report be assembled from the phase reports and validation evidence.
