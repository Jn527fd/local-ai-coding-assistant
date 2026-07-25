# Phase 6 completion report

Date: July 18, 2026

## Status

Phase 6 is complete. Service-driven frontend operations now use the shared `AsyncState<T>` lifecycle, errors are normalized into the approved categories, and every mutation has an explicit execution and rollback policy.

The Phase 6 asynchronous-state baseline was reviewed and approved before Phase 7 began.

## Shared asynchronous state

`src/services/asyncState.ts` defines the single operation-state contract:

```ts
type AsyncStatus = "idle" | "pending" | "success" | "error"

interface AsyncState<T> {
  status: AsyncStatus
  data?: T
  error?: AppError
}
```

The module also exports typed constructors for idle, pending, success, and error states. These prevent partial combinations such as a pending flag paired with a stale error string.

The contract is now used for:

- Session restoration and sign-out state.
- Login and the multi-step signup service requests.
- Conversation-list loading, pagination, retry, and error recovery.
- Conversation rename and delete mutations.
- Message-send request state and accepted-message metadata.
- System-prompt persistence.
- Conversation configuration persistence.
- Source uploads.
- Shared confirmed mutations such as source deletion and prompt clearing.

Existing message streaming statuses and per-file processing statuses remain domain states because they represent persistent entity lifecycles, not the four-state lifecycle of a single server operation.

## Error normalization

`AppErrorCode` now uses the Phase 6 categories:

- `validation`
- `unauthorized`
- `forbidden`
- `not_found`
- `conflict`
- `rate_limited`
- `offline`
- `timeout`
- `server`
- `unknown`

HTTP response mapping handles 400/422, 401, 403, 404, 408, 409, 429, 5xx, and 504 responses. Aborted requests normalize to timeout errors, offline browser state normalizes to an offline error, and unrecognized thrown values receive a safe unknown error.

Local workflow validation uses `validationError()` so client-side validation failures carry the same typed category as server validation responses.

## Mutation and rollback policies

`src/services/mutationPolicies.ts` is a typed, exhaustive registry for every mutation in the current service contracts. Adding a mutation to the `MutationOperation` union without adding a policy is a TypeScript error.

The registry distinguishes:

- `pessimistic`: UI state changes only after the service succeeds.
- `optimistic`: UI updates immediately and specifies the state restored on failure.
- `acknowledged`: input remains intact until the service accepts the operation.

Covered mutations include authentication, email verification, account creation, conversation creation/rename/delete/configuration, message send/cancel/retry, and source upload/delete/retry.

The conversation configuration workflow was already optimistic, but previously lacked rollback. It now captures the previous conversation-specific configuration and restores it if persistence fails. Message sending continues to clear composer content only after the stream emits its accepted event.

## Files changed for Phase 6

- `src/services/asyncState.ts`
- `src/services/errors.ts`
- `src/services/index.ts`
- `src/services/mutationPolicies.ts`
- `src/services/mock/createMockServices.ts`
- `src/api/client.ts`
- `src/auth/AuthProvider.tsx`
- `src/routes/AuthRoutes.tsx`
- `src/features/auth/AuthScreens.tsx`
- `src/App.tsx`
- `docs/PHASE_5_COMPLETION.md`
- `docs/PHASE_6_COMPLETION.md`

## Browser regression validation

The running Vite preview was exercised through the browser. Verified behaviors:

- Invalid login transitions to a normalized unauthorized error without clearing the entered credentials.
- Valid login transitions through pending to the authenticated chat route.
- Invalid email signup transitions to the service validation error and remains editable.
- Empty conversation history loads successfully.
- Sending a message creates a stable conversation and exits pending state after the service completes.
- Deterministic failed generation continues to render its Retry action.
- Conversation rename completes and updates both the sidebar and transcript heading.
- Conversation deletion completes and returns to an immediately usable empty-chat composer.
- Model configuration changes transition to the visible “Configuration saved” state.

## Validation commands and results

- `node_modules\\.bin\\oxfmt.cmd src` — passed; 35 source files checked/formatted.
- `node_modules\\.bin\\tsc.cmd --noEmit` — passed with no TypeScript errors.
- `node_modules\\.bin\\vite.cmd build` — passed; 50 modules transformed.
- `git diff --check` — passed. Git emitted only the repository's existing LF-to-CRLF checkout warnings.
- Error-code scan — no legacy `authentication`, `authorization`, or `network` error codes remain.

Production build output:

- JavaScript: 324.70 kB (97.68 kB gzip)
- CSS: 36.84 kB (8.26 kB gzip)
- HTML: 0.65 kB (0.34 kB gzip)

The repository still has no lint script or automated test suite, so neither command was available in Phase 6.

## Setup

No new dependency, environment variable, migration, database, or backend setup is required. The new modules are frontend TypeScript contracts and state helpers.

## Phase boundary

The Phase 6 gate was reviewed and explicitly approved. Phase 7 is documented separately in `docs/PHASE_7_COMPLETION.md`.
