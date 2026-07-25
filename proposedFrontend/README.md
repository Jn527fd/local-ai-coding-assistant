# LocalChat frontend

LocalChat is a frontend-complete React chat prototype prepared for a backend integration handoff. It includes routed authentication screens, conversation management, streamed mock responses, conversation-scoped system prompts and model settings, source management, accessible modal and keyboard behavior, responsive layouts, automated tests, and CI validation.

The application currently runs entirely against deterministic in-browser mock services. It does not send chat, authentication, or source data to a real server.

The completed implementation and validation evidence are recorded in [the final frontend handoff report](docs/FINAL_HANDOFF_REPORT.md).

## Supported toolchain

- Node.js 22.x
- pnpm 11.9.x

The CI workflow uses Node.js 22 and pnpm 11.9.0. Match those versions locally when reproducing CI results.

## Install and run locally

1. Install Node.js 22.
2. Enable or install pnpm 11.9.0:

   ```bash
   corepack enable
   corepack prepare pnpm@11.9.0 --activate
   ```

3. Copy the environment template:

   ```bash
   cp .env.example .env.local
   ```

   In PowerShell:

   ```powershell
   Copy-Item .env.example .env.local
   ```

4. Install exactly from the lockfile:

   ```bash
   pnpm install --frozen-lockfile
   ```

5. Start Vite:

   ```bash
   pnpm dev
   ```

The default local URL is `http://localhost:8443`. Figma Make may provide a different `PORT`; Vite reads it automatically. The repository also includes `run-local.sh` for Bash environments.

Demo credentials:

- Username: `test`
- Password: `test`
- Signup email: `test@email.com`
- Verification code: `12345`

## Environment variables

| Variable | Default | Current behavior |
| --- | --- | --- |
| `VITE_API_BASE_URL` | `/api` | Used by `src/api/index.ts` when constructing the generic JSON API client. |
| `VITE_USE_MOCK_API` | `true` in the example | Selects deterministic mocks unless explicitly set to `false`. HTTP mode currently connects sign in, sign out, and session restore to the existing backend auth routes; other services return clear not-connected errors until their adapters are implemented. |
| `PORT` | `8443` | Vite development and preview port. This is a process variable, not a browser-exposed Vite variable. |
| `FIGMA_PUBLIC_URL` | unset | Optional Figma Make deployment base path used by `vite.config.ts`. |

Only variables prefixed with `VITE_` are exposed to browser code. Never place secrets, private API keys, or server credentials in them.

## Application routes

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | Public | Redirects to `/chat` for an authenticated session or `/login` otherwise. |
| `/login` | Public | Username/password login. |
| `/signup` | Public | Signup method selection. |
| `/signup/email` | Public | Email, verification-code, and password signup flow. |
| `/forgot-password` | Public placeholder | Reserved password-recovery route. |
| `/reset-password` | Public placeholder | Reserved password-reset route. |
| `/chat` | Protected | Empty/new conversation workspace. |
| `/chat/:conversationId` | Protected | Deep link to a conversation. |
| `/profile` | Protected | Editable local profile, preferences, account metadata, and export. |
| `/settings` | Protected | Device-local appearance and chat preferences. |
| `/help` | Protected placeholder | Reserved help route. |
| `*` | Public | Not-found screen. |

Protected routes preserve the attempted path in router state and return to it after successful login. Session restoration finishes before a protected route decides whether to render or redirect.

## Architecture

```text
src/main.tsx
  BrowserRouter + AuthProvider
    src/routes/                 route and protection boundaries
      src/App.tsx               conversation-page orchestration
        src/features/           auth, chat, conversations, configuration, sources
        src/components/         reusable modal and toolbar primitives
        src/services/           UI-facing service contracts and implementations
          src/services/mock/    deterministic in-browser implementation
        src/api/                transport-level JSON client for a future HTTP adapter
        src/domain/             domain models, DTOs, and defaults
```

UI modules depend on the typed `appServices` facade rather than calling `fetch` directly. `src/App.tsx` coordinates conversation-page state and mutations; service contracts define the backend seam. Async view state is represented consistently through `idle`, `pending`, `success`, and `error` states.

## Service interfaces

`src/services/contracts.ts` defines five frontend-facing interfaces:

- `AuthService`: sign in/out, restore a session, request and verify an email code, create an account, and request an OAuth redirect.
- `ConversationService`: paginate, fetch, create, rename, delete, and update conversation configuration.
- `MessageService`: send or stream a message, cancel generation, and retry a failed/stopped response.
- `SourceService`: list, upload, delete, summarize, and retry source processing.
- `ProfileService`: load and update the profile, upload an avatar, and export profile data.

`AppServices` groups those interfaces. Domain return types live in `src/domain/models.ts`; transport request/response types live in `src/domain/dtos.ts`. Mutation timing and rollback expectations are centralized in `src/services/mutationPolicies.ts` and should be preserved by a real adapter.

The Profile feature keeps its presentation in `src/features/profile/ProfileForm.tsx` and its service-backed state in `src/features/profile/ProfilePage.tsx`. Mock profile changes use versioned browser storage so the demo survives reloads. Real profile integration should replace the four methods in `src/services/mock/createMockProfileService.ts` with `GET /api/profile`, `PATCH /api/profile`, `POST /api/profile/avatar`, and `GET /api/profile/export`. Profile deletion is intentionally not offered and is not part of the frontend service contract. The frontend does not call these endpoints directly and does not hardcode a production API URL.

Device settings are stored separately under the versioned `localchat.settings.v1` browser-storage key. `src/features/settings/settingsStorage.ts` is the single frontend boundary for loading, validating, applying, and persisting those preferences. These settings are intentionally local to the browser until product and backend teams decide whether any should follow a user between devices.

## Replacing mocks with real services

`VITE_USE_MOCK_API=false` selects the HTTP service factory in
`src/services/http/createHttpServices.ts`. The adapter maps sign in, sign out,
session restore, account status, and API-key updates to the existing backend
routes `/auth/login`, `/auth/logout`, `/auth/me`, `/account/status`, and
`/account/api-key`. Other service methods still return clear not-connected
errors until their adapters are implemented. This keeps the runtime switch
testable without pretending full backend integration is complete.

Backend integration should proceed as follows:

1. Continue replacing not-connected methods in `src/services/http/createHttpServices.ts` with real adapter implementations that satisfy every `AppServices` interface.
2. Use `createApiClient` with `VITE_API_BASE_URL` for JSON requests.
3. Use `appServices.account.getStoredApiKey()` when future AI/data adapters need the Bearer API key. The key is stored under the compatibility key `local-ai-coding-assistant.api-key`.
4. Implement the streaming method as an `AsyncIterable<MessageStreamEvent>` over SSE or another agreed transport.
5. Map backend payloads into domain models at the adapter boundary. Do not expose transport response shapes directly to components.
6. Map HTTP and transport failures into `AppError` and preserve server `X-Request-ID` values.
7. Select mock or HTTP services once in `src/services/index.ts`, for example from `VITE_USE_MOCK_API`.
8. Keep mock services available for tests and local frontend development.

The proposed transport contract is documented in [the OpenAPI draft](docs/backend-api.openapi.yaml). That draft is a handoff proposal, not a deployed API.

## Authentication assumptions

- The frontend expects an `AuthSession` with an access token, ISO-8601 expiration timestamp, and user record.
- The mock stores the complete session in `sessionStorage`; a production implementation should choose secure token storage with the backend/security team. An `HttpOnly`, `Secure`, same-site cookie is preferable when architecture permits it.
- If bearer tokens are used, the API client expects `Authorization: Bearer <token>`.
- Session restoration returns a session or `null`; expired sessions are treated as unauthenticated.
- `401` means authentication is missing or expired. `403` means the authenticated user lacks permission.
- Sign-out clears frontend session state even when the remote sign-out request fails, preventing stale credentials from lingering.
- OAuth buttons currently return a mock redirect. The real backend must validate `returnTo` against an allowlist and own OAuth/SSO state, nonce, callback, and account-linking behavior.
- Email verification expiry, resend throttling, attempt limits, password policy, and rate limiting must be enforced by the backend even though the frontend provides validation and countdown UI.
- The current client password checks require at least eight characters, uppercase, lowercase, a number, and a special character.

## Conversation scope and persistence

System prompts, model configuration, selected source IDs, and temporary status belong to one conversation. A newly created conversation starts from fresh defaults. Switching conversations loads that conversation's saved configuration; values must never be copied implicitly from the previously active conversation.

For local demo use, the mock service stores saved conversations, messages, configuration, and source metadata in versioned `localStorage`. This keeps stable `/chat/:conversationId` routes valid across a full page reload without preloading demo conversations. Temporary conversations are deliberately excluded. A response interrupted by a reload is restored as stopped and retryable. This browser storage is only the mock adapter's persistence mechanism; the production HTTP adapter should load the same domain models from the backend.

Saving configuration changes future requests only. Existing messages are not regenerated. Source deletion removes the deleted source ID from every affected conversation. Temporary conversations are excluded from saved-history lists; the backend must decide whether they are never persisted or are retained with a short server-side lifetime.

Conversation creation must return a stable server ID before the frontend commits a new route. Deleting the active or last conversation returns the UI to another valid conversation or the empty `/chat` composer without disabling input.

## Message streaming assumptions

The UI consumes these ordered events:

1. `accepted`: contains the persisted user message and a pending assistant message. Only after this event does the composer clear.
2. Zero or more `delta`: each identifies the assistant message and appends text.
3. Exactly one terminal `complete` or `failed` event.

The proposed wire format is Server-Sent Events using event names `accepted`, `delta`, `complete`, and `failed`. The adapter must preserve event order and message IDs. A stream that disconnects without a terminal event should become a retryable normalized error. Cancellation must be idempotent; retry returns a replacement completed message for the same message ID unless the backend team explicitly chooses a new-version model.

The UI does not currently implement automatic stream reconnection or resume tokens. The backend and frontend teams must decide whether reconnection replays events, resumes from an event ID, or requires a retry.

## Upload limits and accepted types

### Composer attachments

- Maximum five attachments per message.
- Maximum 10 MiB per file.
- Empty and duplicate files are rejected.
- Accepted media types: `image/png`, `image/jpeg`, `image/webp`, `application/pdf`, `text/plain`, `text/markdown`, and `text/csv`.

The current demo prepares composer attachments locally and passes attachment metadata with the send request. A real backend needs either a multipart attachment endpoint or a presigned-upload flow that returns `attachmentIds` before message submission.

### Sources

- Maximum ten source files per upload operation.
- Maximum 25 MiB per file.
- Empty files and duplicate filenames are rejected.
- Accepted media types: PDF, DOCX, XLSX, plain text, PNG, and JPEG.
- Source processing states: `uploading`, `processing`, `ready`, and `failed`.

### Modelfile import

The system-prompt dialog accepts a UTF-8 text Modelfile up to 1 MiB. It is read locally into the prompt editor and is not a source upload. Saving persists only the resulting prompt text.

Browser validation is for feedback only. The backend must repeat all count, size, content-type, authorization, malware, filename, and content validation. Do not trust the browser-provided MIME type or filename.

## Error response contract

The API client sends `Accept: application/json` and an `X-Request-ID`. JSON bodies use `Content-Type: application/json`. The backend should echo or replace `X-Request-ID` in every response and use one error envelope:

```json
{
  "code": "validation",
  "message": "The title is required.",
  "requestId": "req_01J...",
  "fieldErrors": {
    "title": "Enter a conversation title."
  }
}
```

Expected mappings:

| HTTP status | Frontend error code | Meaning |
| --- | --- | --- |
| `400`, `422` | `validation` | Invalid body, field, file, or state transition. |
| `401` | `unauthorized` | Missing or expired authentication. |
| `403` | `forbidden` | Authenticated but not permitted. |
| `404` | `not_found` | Requested resource does not exist or is not visible. |
| `409` | `conflict` | Stale version, duplicate, or state conflict. |
| `429` | `rate_limited` | Request throttled; include `Retry-After` when possible. |
| `408`, `504` | `timeout` | Request or upstream operation timed out. |
| `500`-`599` | `server` | Backend or dependency failure. |

The current `ApiClient` reads `message` from error JSON and normalizes status and request ID. The real adapter should also retain structured `code` and `fieldErrors` once those are added to `AppError`.

## Validation commands

```bash
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm build
```

`pnpm validate` runs formatting, linting, type checking, Vitest, and the build. Playwright remains a separate command. CI installs from the lockfile and runs `pnpm validate` against mock services.

## Backend decisions still required

- Cookie session versus bearer-token storage and refresh-token rotation.
- SSE resume/reconnect behavior and server-side cancellation semantics.
- Direct multipart attachment upload versus presigned object-storage upload.
- Virus scanning, document parsing, retention, and deletion guarantees.
- Whether temporary conversations are never persisted or expire later.
- Optimistic concurrency/version fields for rename and configuration writes.
- Canonical available-model identifiers, capabilities, permissions, and fallback behavior.
- OAuth/SSO providers, callback URLs, account linking, and enterprise tenant discovery.
- Password reset token and email delivery behavior for placeholder routes.

## Contract references

- [OpenAPI backend draft](docs/backend-api.openapi.yaml)
- [Service contracts](src/services/contracts.ts)
- [Domain models](src/domain/models.ts)
- [Transport DTOs](src/domain/dtos.ts)
- [Mutation policies](src/services/mutationPolicies.ts)
