# Final frontend handoff report

**Project:** LocalChat frontend  
**Report date:** July 23, 2026
**Status:** Frontend implementation and final validation complete; ready for backend integration handoff

## Executive summary

The repository has completed Phases 0 through 10 of `FRONTEND_HANDOFF_GUIDE.md` and the separate final validation gate. The original visual prototype is now a routed, typed, accessible, responsive, tested React application with backend-replaceable service boundaries.

The application still uses deterministic browser-side mock services. This is intentional: no backend, database, production authentication, model provider, or document-processing infrastructure was added. Active controls are implemented against typed service contracts; controls that require product or backend work are visibly disabled or presented as explicit placeholders.

The final reload/deep-link blocker was resolved by adding versioned local mock persistence. Saved conversation URLs now survive a full page reload, while temporary conversations remain memory-only. All required automated checks pass.

## 1. Architecture and files added or moved

The application is composed through these boundaries:

```text
src/main.tsx
  BrowserRouter
    AuthProvider
      AppRoutes
        protected and public route screens
          App.tsx conversation-page orchestration
            components/ shared UI primitives
            features/ feature-owned UI
            domain/ frontend models, DTOs, and defaults
            services/ application contracts and adapters
            api/ reusable HTTP client boundary
```

The original monolithic `App.tsx` was decomposed into feature-owned modules. The important additions are:

- `src/components/`: centered modal, confirmation modal, and toolbar-button primitives.
- `src/features/auth/`: login, signup selection, and email-signup screens.
- `src/features/chat/`: transcript and composer behavior.
- `src/features/conversations/`: sidebar, recent/search views, rename/delete flows, and date formatting.
- `src/features/configuration/`: right toolbar, system-prompt modal, and chat configuration.
- `src/features/sources/`: source selection, upload state, summaries, retry, and deletion.
- `src/features/profile/`: editable local profile, avatar, export, and service-backed state.
- `src/features/settings/`: device-local appearance and chat preferences.
- `src/routes/`: explicit public, protected, deep-link, placeholder, and not-found routes.
- `src/auth/`: centralized session provider and restoration lifecycle.
- `src/domain/`: typed models, DTOs, and clean conversation defaults.
- `src/services/`: service contracts, asynchronous state helpers, normalized errors, mutation policies, mock adapter, and composition root.
- `src/api/`: centralized JSON HTTP client prepared for a real adapter.
- `src/test/` and `e2e/`: persistent unit, component, network, accessibility, and browser test infrastructure.
- `.github/workflows/validate.yml`: lockfile-enforced validation on pushes and pull requests.
- `.env.example`, `README.md`, and `docs/backend-api.openapi.yaml`: backend handoff and setup documentation.

No existing application file was moved in a way that changes its public import role. `src/App.tsx` remains the conversation-page orchestrator, and `src/main.tsx` remains the entry point.

## 2. Domain and API contracts introduced

`src/domain/models.ts` defines the frontend domain, including:

- Authenticated session and user records.
- Conversations and conversation summaries.
- Messages with pending, streaming, complete, stopped, and failed states.
- Attachments and source documents with processing states.
- Conversation-owned model configuration, system prompt, selected source IDs, and temporary status.
- Pagination and OAuth redirect models.

`src/domain/dtos.ts` keeps transport request and response shapes separate from UI state. It covers authentication, conversation creation and updates, message requests, attachments, source operations, and model configuration.

`src/services/contracts.ts` exposes five UI-facing interfaces:

- `AuthService`
- `ConversationService`
- `MessageService`
- `SourceService`
- `ProfileService`

`AppServices` groups those interfaces. Components depend on this facade and contain no direct `fetch()` calls.

`src/api/client.ts` provides the transport foundation for a future adapter: base URL handling, JSON serialization, authentication headers, request IDs, abort signals, response parsing, and normalized HTTP errors. `docs/backend-api.openapi.yaml` proposes the backend contract for authentication, conversations, configuration, messages and SSE streaming, attachments, sources, and model availability.

`src/services/mutationPolicies.ts` records whether each mutation is pessimistic, optimistic, or acknowledged and defines its rollback expectations. A real adapter should preserve those user-visible semantics.

## 3. Mock services and how to replace them

`src/services/mock/createMockServices.ts` implements every service contract with deterministic in-browser behavior. It provides controllable latency, one-shot failure injection, stable generated IDs, message streaming events, authentication and signup fixtures, conversation CRUD, retry and cancellation, source workflows, and conversation configuration.

Saved mock conversations, messages, configuration, and source metadata use versioned `localStorage` under `localchat.mock-data.v1`. The mock session uses `sessionStorage`. No conversations are preloaded. Temporary conversations are excluded from persistent storage. If a reload interrupts a pending or streaming mock response, it is restored as stopped and retryable instead of remaining permanently pending.

The mock Profile service keeps its fixture in `src/services/mock/mockProfileData.ts` and stores saved presentation preferences under the versioned `localchat.mock-profile.v1` key. Profile presentation and data-access state are separated, and the adapter exposes independent load, update, avatar, and export methods for backend replacement. Profile deletion is an explicit product exclusion and is not exposed by the UI or frontend service contract.

Device-local appearance and chat preferences use the versioned `localchat.settings.v1` key through `src/features/settings/settingsStorage.ts`. This single boundary validates stored values and keeps the conversation page synchronized with the Settings screen.

The replacement seam is `src/services/index.ts`. Backend engineers should:

1. Implement an HTTP adapter satisfying `AppServices`, preferably under `src/services/http/`.
2. Use `src/api/client.ts` for ordinary JSON requests.
3. Connect its access-token callback or replace bearer-token handling with the chosen cookie-session design.
4. Implement `MessageService.stream()` using the agreed SSE, fetch-streaming, or WebSocket transport.
5. Convert backend payloads to domain models at the adapter boundary.
6. Convert transport failures to `AppError` and retain server request IDs.
7. Select the mock or HTTP adapter once in `src/services/index.ts`.
8. Keep the mock adapter for deterministic frontend development and tests.

`VITE_USE_MOCK_API` is documented but intentionally not wired yet. Setting it to `false` does not currently select an HTTP service.

## 4. Completed and intentionally deferred controls

### Completed

- Login, logout, session restoration, signup selection, and the complete demo email-signup flow.
- Protected routes, requested-page redirects, deep-linked conversations, and not-found handling.
- New conversation, first-message creation, selection, pagination, filtering, search, recent chats, rename, and confirmed deletion.
- Empty-history and delete-last-conversation recovery with an immediately usable composer.
- Mock message streaming, failure, Stop, Retry, Regenerate, Copy, and Copy code states.
- Multiline composer drafts, attachment preparation, validation, previews, retry, and removal.
- Conversation-scoped system prompts, Modelfile import, prompt clearing, unsaved-change protection, and active-state display.
- Conversation-scoped LLM and vision model configuration.
- Sources search, upload validation, selection, summaries, retry, and confirmed deletion.
- Temporary-chat behavior and explicit exclusion from saved history and mock persistence.
- Profile-menu navigation plus an accessible Settings screen and Help placeholder destination.
- A responsive Profile page with editable presentation preferences, local avatar preview, read-only local-account metadata, validation, dirty-state handling, save feedback, and export.
- Device-local theme, text-size, composer, timestamp, and chat-deletion-confirmation settings with save, cancel, and confirmed reset behavior.

### Intentionally deferred or placeholder-only

- Help page content beyond its stable protected placeholder route.
- Forgot Password and Reset Password beyond stable public placeholder routes.
- Google and company signup beyond typed mock OAuth redirect previews.
- Dictation and voice chat; both controls are visibly disabled with accessible explanations.
- Real model discovery, model execution, embeddings, vector search, OCR, parsing, reranking, and context compression.
- Actual file transfer, durable document storage, malware scanning, parsing, indexing, and deletion guarantees.
- Production notification delivery for verification codes.
- A runtime HTTP-adapter selector; `VITE_USE_MOCK_API` remains reserved.

No critical control is silently inactive. Backend-dependent controls are disabled, marked as placeholders, or return explicit mock feedback.

## 5. Conversation-scoped state behavior

Each conversation owns its messages, system prompt, model configuration, source IDs, timestamps, and temporary flag. Composer text and attachment drafts are also keyed by conversation in the page state. Switching conversations restores that conversation's values and never copies settings from the previously selected chat.

A message sent from `/chat` creates a conversation with a stable ID before navigating to `/chat/:conversationId`. Deleting the active conversation selects a predictable neighbor or returns to the usable empty composer. Deleting every conversation and sending again creates a fresh saved conversation without requiring a route change or unrelated click.

Saved mock conversations survive reloads through versioned browser storage. Reloading a valid `/chat/:conversationId` restores the route, transcript, configuration, and editable composer. Unknown IDs return to `/chat` after loading completes. Temporary chats remain intentionally memory-only and disappear after a reload.

System-prompt and model updates affect future requests only; previous messages are not modified. Source deletion removes the deleted ID from every affected conversation. Optimistic configuration updates roll back if persistence fails.

## 6. Authentication and routing behavior

`AuthProvider` centrally owns restoration, authenticated, and unauthenticated states plus sign-in, sign-out, and post-signup session refresh. The deterministic credentials are:

- Username: `test`
- Password: `test`
- Signup email: `test@email.com`
- Verification code: `12345`

The mock session is restored from `sessionStorage` and rejected when expired or malformed. Sign-out clears the mock session and returns the user to Login. Production token storage remains a security and backend decision; an `HttpOnly`, `Secure`, same-site cookie is preferred where the architecture permits it.

Public routes include Login, signup selection, email signup, password placeholders, and the not-found screen. Chat, Profile, Settings, and Help are protected. An unauthenticated request for a protected route is redirected to Login and returned to its complete original path after successful authentication. Authenticated users are redirected away from Login and Signup.

## 7. Accessibility and responsive improvements

Accessibility work includes:

- A skip link and named navigation, tools, main-content, composer, and transcript landmarks.
- Accessible names and state attributes for icon buttons and toolbar controls.
- ARIA menu semantics and Arrow, Home, End, and Escape support for profile and conversation menus.
- Shared centered dialogs with initial focus, focus trapping, Escape/backdrop policies, nested-confirmation focus handling, and focus restoration.
- Conversation-log and message semantics plus polite status announcements for assistant lifecycle changes.
- Visible `:focus-visible` treatment, improved secondary and placeholder contrast, and reduced-motion support.
- Accessible source, attachment, retry, copy, and image-preview labels.

Responsive behavior was verified at 360, 430, 768, 1024, and 1440 pixels. Below 768 pixels the left navigation becomes a modal drawer and the right rail becomes a safe-area-aware bottom toolbar. Composer controls, dialogs, source lists, menus, long titles, long messages, long prompts, dynamic viewport height, and 200% zoom behavior were adjusted to avoid horizontal overflow and control overlap.

## 8. Tests added and validation commands run

Persistent test coverage includes:

- Domain-default and date-formatting unit tests.
- Mock-service tests for authentication, signup, conversation isolation, conversation mutations, streaming, failure/retry, sources, reload persistence, temporary-chat exclusion, and interrupted-stream recovery.
- API-client tests through Mock Service Worker.
- React component tests for authentication, transcript states, centered-modal focus/dismissal, system-prompt draft behavior, Profile, and Settings.
- Six Playwright scenarios covering keyboard authentication, session restoration, conversation workflows and deletion edge cases, exact deep-link reload restoration, prompt/settings isolation, message failure recovery, source workflows, signup failures, successful signup, and the export-only Profile workflow.
- An authenticated Axe scan within the browser suite.

Final automated validation:

| Command | Result |
| --- | --- |
| `pnpm install --frozen-lockfile` | Passed; lockfile already current. |
| `pnpm format:check` | Passed; 59 files checked. |
| `pnpm lint` | Passed with zero errors and warnings. |
| `pnpm typecheck` | Passed. |
| `pnpm test` | Passed; 12 files and 41 tests. |
| `pnpm test:e2e` | Passed; 6 browser scenarios. |
| `pnpm build` | Passed; 56 modules transformed. |

Final production output:

- JavaScript: 355.34 kB, 104.98 kB gzip.
- CSS: 53.02 kB, 11.29 kB gzip.
- HTML: 0.65 kB, 0.34 kB gzip.

Additional final-gate results:

- Keyboard-only walkthrough: passed through the Playwright sign-in/sign-out flow.
- Screen-reader/accessibility-tree smoke test: named landmarks, dialogs, headings, controls, and text boxes were exposed correctly.
- Modal focus test: initial text-area focus, Escape dismissal, and trigger focus restoration passed.
- Automated accessibility scan: zero violations in the authenticated scenario.
- Responsive walkthrough: passed at 360, 430, 768, 1024, and 1440 pixels with no horizontal overflow.
- Slow-network simulation: Login remained usable with 250 ms request delays and no console errors.
- Offline simulation: browser offline state and navigation failure were detected; HTTP service-error behavior cannot be fully exercised until the HTTP adapter exists.
- Mock failure simulation: deterministic generation failure displayed recovery UI and Retry completed successfully.
- Refresh and deep-link testing: exact saved-conversation URL, transcript, and composer restored successfully after full reload.
- Browser console check: no warnings or errors were observed during the final walkthrough.

## 9. Environment variables and setup steps

Supported local toolchain:

- Node.js 22.x
- pnpm 11.9.x

Environment variables:

| Variable | Purpose | Current state |
| --- | --- | --- |
| `VITE_API_BASE_URL` | Base URL for the generic HTTP client. | Active in `src/api/index.ts`; defaults to `/api`. |
| `VITE_USE_MOCK_API` | Planned mock/HTTP adapter selection. | Reserved and not yet read at runtime. |
| `PORT` | Vite development/preview port. | Defaults to `8443`. |
| `FIGMA_PUBLIC_URL` | Optional Figma Make base path. | Used only when supplied. |

Setup:

```bash
corepack enable
corepack prepare pnpm@11.9.0 --activate
cp .env.example .env.local
pnpm install --frozen-lockfile
pnpm dev
```

PowerShell users can replace the copy command with:

```powershell
Copy-Item .env.example .env.local
```

The default application URL is `http://localhost:8443`. No database, migration, secret, external API, model server, or backend process is required to run the current mock frontend. Browser-exposed `VITE_*` variables must never contain secrets.

## 10. Remaining backend assumptions and unresolved product decisions

Backend and product teams must resolve:

- Cookie sessions versus bearer tokens, refresh rotation, revocation, expiry, CSRF protection, and cross-origin policy.
- User ownership and authorization for every conversation, message, attachment, and source.
- Production OAuth/SSO providers, return-URL allowlisting, state/nonce handling, tenant policy, callbacks, and account linking.
- Verification-code delivery, expiry, resend throttling, attempt limits, password policy, password reset, and rate limiting.
- Whether device-local Settings should remain browser-specific or later synchronize through a user account.
- Conversation persistence, stable IDs, pagination ordering, deletion semantics, and optimistic concurrency/version fields.
- SSE or alternative streaming transport, event ordering, cancellation idempotency, disconnect recovery, resume/replay behavior, and retry identity.
- Canonical model identifiers, model permissions, availability discovery, fallbacks, and configuration validation.
- Attachment and source upload strategy: multipart versus presigned uploads, size enforcement, progress, scanning, object storage, retention, parsing, indexing, and deletion guarantees.
- Temporary-chat server behavior: never persisted versus short-lived storage and expiry.
- Whether source selection applies to the next message only or remains conversation configuration; the current frontend treats it as conversation-scoped.
- Production observability, request-ID propagation, audit events, analytics, privacy, retention, and compliance requirements.
- Whether offline operation is unsupported, read-only, queued, or synchronized later.

Profile deletion is not an unresolved backend decision: the approved product behavior is to omit it. It is intentionally absent from the frontend UI, service contract, mock adapter, and handoff manifest.

The OpenAPI proposal is a starting contract, not a deployed service specification. Backend engineers should review it with frontend, product, security, and platform owners before implementation.

## Handoff conclusion

The frontend is ready to hand to backend engineers. Its active workflows are routed through typed, replaceable service contracts; critical conversation state is isolated; the local demo is reload-safe; inactive functionality is explicit; and the required automated validation suite passes. Backend work can proceed at the service-adapter boundary without embedding transport calls in UI components or redesigning the current frontend state model.
