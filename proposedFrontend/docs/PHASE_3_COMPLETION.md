# Phase 3 completion report

Date: July 18, 2026

## Status

Phase 3 is complete. Backend-facing behavior now sits behind typed service contracts, the prototype uses replaceable mock implementations, and a centralized API client placeholder is ready for a future HTTP implementation.

Phase 4 has not started. No router, authentication provider, protected routes, redirect handling, URL-based conversation selection, or session-restoration UI was introduced.

## Service contracts

`src/services/contracts.ts` defines:

- `AuthService`
- `ConversationService`
- `MessageService`
- `SourceService`
- `AppServices`

The contracts cover authentication and email verification, conversation list/get/create/rename/delete/configuration, message send/cancel/retry, and source list/upload/delete/summary operations.

The interfaces accept request DTOs and return frontend domain objects. UI modules do not import mock implementation modules.

## Mock implementations

`src/services/mock/createMockServices.ts` provides an in-memory implementation of every service contract.

The mocks include:

- Shared conversation, message, source, verification, and session state
- Generated mock server IDs
- ISO timestamps
- Default randomized latency of 90–180 milliseconds
- Authentication validation for the existing demo credentials
- Email and verification-code validation for the existing signup demo
- Conversation CRUD and configuration persistence
- Message storage and generic assistant responses
- Source listing, upload contracts, deletion, and summaries
- Message cancellation and retry contracts

The returned `MockServiceControl` supports:

- `setLatency(minimumMs, maximumMs)`
- `failNext(operation, error)`
- `reset()`

This provides deterministic control for future development and automated tests without exposing mock modules to UI components.

## Composition root

`src/services/index.ts` is the only composition point that selects the mock implementations. It exports `appServices` using the `AppServices` interface.

The UI imports `appServices` or service interface types from this module. Replacing the mock bundle with HTTP-backed implementations will therefore not require components to import a different mock or API module.

## UI integration

The existing frontend now uses service contracts for:

- Valid and invalid sign-in attempts
- Sign-out
- Email verification requests
- Verification-code validation
- Account creation
- Conversation loading
- Conversation creation, rename, and deletion
- Conversation-specific configuration updates
- Message submission and conversation refresh
- Source loading, deletion, and summary retrieval

Local React state remains the view state/cache for the prototype. Pending-state standardization and full error-recovery UX are intentionally deferred to their later phases.

## Central API client

`src/api/client.ts` centralizes:

- Base URL resolution
- JSON request serialization
- JSON response parsing
- Authentication headers through a token accessor
- Request ID generation and `X-Request-ID` headers
- Caller-provided abort signals
- HTTP success and error handling
- HTTP status-to-error-category mapping
- Normalized `AppError` results
- Injectable `fetch` implementation for future tests

`src/api/index.ts` creates the placeholder client using `VITE_API_BASE_URL`, with `/api` as the default. The token accessor is intentionally left for the Phase 4 session provider.

No component contains a direct `fetch()` call.

## Files changed

Added:

- `src/api/client.ts`
- `src/api/index.ts`
- `src/services/contracts.ts`
- `src/services/errors.ts`
- `src/services/index.ts`
- `src/services/mock/createMockServices.ts`
- `docs/PHASE_3_COMPLETION.md`

Updated:

- `src/App.tsx`
- `src/domain/dtos.ts`
- `src/domain/models.ts`
- `src/features/auth/AuthScreens.tsx`
- `docs/PHASE_2_COMPLETION.md`

## Browser verification

The following service-backed flows were exercised in the running application:

- Invalid login returned the normalized mock authentication error.
- Valid `test` / `test` login opened the application.
- Source documents loaded through `SourceService.list()`.
- A source summary loaded through `SourceService.getSummary()`.
- Sending a first message created a conversation through `ConversationService`, sent through `MessageService`, and rendered the refreshed conversation.
- Starting another conversation used `ConversationService.create()` and retained the previous conversation.
- A saved system prompt persisted through `ConversationService.updateConfiguration()` and was restored after switching conversations.
- Email signup requested verification through `AuthService`.
- Code `12345` advanced through `AuthService.verifyEmailCode()` to password creation.

No visual regression was observed in these flows.

## Automated validation

The following commands completed successfully using the configured workspace Node runtime:

```powershell
.\node_modules\.bin\oxfmt.cmd src
.\node_modules\.bin\tsc.cmd --noEmit
pnpm run build
git diff --check
```

Additional boundary scans confirmed:

- UI and feature modules do not import `services/mock`.
- No direct `fetch()` calls exist outside the centralized API abstraction.
- No Phase 4 routing dependency or route implementation was introduced.

Production build result:

- Vite 8.0.3
- 34 modules transformed
- JavaScript bundle: 258.87 kB (76.39 kB gzip)
- CSS bundle: 30.86 kB (6.97 kB gzip)
- Build completed successfully

The repository still has no lint command or automated test suite, so neither was available to run. The mock failure controller and injectable API transport are ready for that future test infrastructure.

## Phase boundary

Phase 3 was reviewed and explicitly approved by the user before Phase 4 began.
