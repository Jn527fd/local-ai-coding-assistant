# LocalChat Frontend Readiness Guide

## Purpose

This document guides a Codex agent through converting the current LocalChat visual prototype into a maintainable, tested frontend that can be handed to backend engineers.

The goal is **not** to build a production backend. The goal is to provide:

- A clean frontend architecture.
- Backend-ready TypeScript contracts.
- Mock services that use the same contracts as the eventual backend.
- Complete loading, success, empty, and error states.
- Tested and accessible user workflows.
- Clear integration documentation.

Preserve the current visual direction unless a change is required for accessibility, responsiveness, or a missing state.

## Current project

- React 19
- Vite 8
- TypeScript in strict mode
- Tailwind CSS 4 is installed
- Main application: `src/App.tsx`
- Global styles: `src/index.css`
- Package manager: pnpm
- Local development port: 8443 by default

The current application is a frontend-only prototype. Authentication, signup, conversations, messages, sources, model configuration, and system prompts are held in component state or use hardcoded demo behavior.

## Working rules

1. Read `AGENTS.md`, `package.json`, `src/App.tsx`, and `src/index.css` before editing.
2. Inspect the current Git status and preserve unrelated user changes.
3. Do not implement a real backend, database, authentication server, email provider, model server, or document-processing service.
4. Do not introduce a state-management library unless React context, reducers, and feature hooks are demonstrably insufficient.
5. Avoid visual redesigns. Refactor behavior and structure while preserving the established appearance.
6. Keep the application runnable after every phase.
7. Use small, reviewable changes instead of rewriting the entire application at once.
8. Do not leave clickable controls that silently do nothing. Implement them with mocks, disable them with an explanation, or mark them as intentionally deferred.
9. Keep mock data and mock delays outside UI components.
10. Run validation after every phase and fix regressions before continuing.

## Definition of ready for backend handoff

The frontend is ready when all of the following are true:

- UI components do not directly create fake server responses.
- Every backend-facing action goes through a typed service interface.
- Mock services can be replaced without changing presentation components.
- Authentication and conversation pages have real routes.
- Refreshing the app restores the mock session and mock data where appropriate.
- Conversations own their messages, prompt, model configuration, sources, and temporary status.
- Every asynchronous workflow displays pending, success, empty, and failure states.
- All advertised controls either work or are explicitly disabled.
- Unit, component, and end-to-end tests cover critical workflows.
- Keyboard navigation, focus behavior, and screen-reader labels are verified.
- Phone, tablet, laptop, long-content, and 200% zoom layouts are verified.
- Formatting, linting, type checking, tests, and production build pass.
- Backend engineers have integration documentation and example payloads.

## Target architecture

Use this as a guide rather than an inflexible requirement:

```text
src/
  app/
    App.tsx
    router.tsx
    providers.tsx
  components/
    common/
    modal/
  features/
    auth/
      api/
      components/
      hooks/
      pages/
      types.ts
    conversations/
      api/
      components/
      hooks/
      pages/
      types.ts
    chat/
      components/
      hooks/
      types.ts
    sources/
      api/
      components/
      hooks/
      types.ts
    configuration/
      components/
      types.ts
  services/
    api-client.ts
    contracts.ts
    mock/
  styles/
    tokens.css
    globals.css
  test/
    fixtures/
    setup.ts
```

Prefer feature ownership over a large generic components directory.

## Phase 0: Establish the baseline

- Record the current behavior and important visual states.
- Run the existing formatter, TypeScript check, and production build.
- Create a short inventory of every visible button, form, modal, and workflow.
- Identify which controls work, are mocked, or are inactive.
- Document any known defects before refactoring.

Baseline commands:

```bash
pnpm install
pnpm format -- --check
pnpm exec tsc --noEmit
pnpm build
```

Do not begin structural work while the baseline is failing.

## Phase 1: Decompose the application

Break `src/App.tsx` into feature-focused components without changing behavior.

Extract at minimum:

- Login page
- Signup page and signup steps
- Left conversation sidebar
- Profile menu
- Right configuration toolbar
- Chat transcript
- Composer
- Search Chats modal
- Delete Conversation modal
- System Prompt modal
- Chat Configuration modal
- Sources modal
- Shared centered modal

Move large inline style objects into the existing styling system. Choose a consistent approach:

- Tailwind utilities for component layout and states, or
- Feature-scoped CSS classes plus shared design tokens.

Do not continue expanding a mixture of large inline style objects and global CSS.

Completion criteria:

- `App.tsx` primarily composes routes and providers.
- Feature components have focused props and responsibilities.
- No visual or behavioral regressions.
- The production build still passes.

## Phase 2: Define frontend domain models

Create explicit types that can map cleanly to backend DTOs. Do not derive API types from mock arrays.

At minimum model:

```ts
type MessageRole = "user" | "assistant" | "system"
type MessageStatus = "pending" | "streaming" | "complete" | "failed"

interface ChatAttachment {
  id: string
  filename: string
  mediaType: string
  size: number
  status: "uploading" | "ready" | "failed"
  url?: string
}

interface ChatMessage {
  id: string
  conversationId: string
  role: MessageRole
  content: string
  status: MessageStatus
  createdAt: string
  attachments: ChatAttachment[]
  error?: string
}

interface ModelConfiguration {
  llmModel: string
  visionModel: string
  embedder?: string
  pdfParser?: string
  vectorDatabase?: string
  ocrEngine?: string
  contextCompressor?: string
  reranker?: string
}

interface Conversation {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
  systemPrompt: string
  modelConfiguration: ModelConfiguration
  sourceIds: string[]
  temporary: boolean
}

interface SourceDocument {
  id: string
  filename: string
  mediaType: string
  size: number
  createdAt: string
  status: "uploading" | "processing" | "ready" | "failed"
  summary?: string[]
  error?: string
}
```

Also define request and response DTOs separately when their shape differs from frontend domain objects.

Completion criteria:

- Conversation-specific configuration is stored on the conversation.
- Selecting a conversation loads only that conversation's data.
- No prompt, source, or model setting leaks between conversations.
- Timestamps are stored as ISO values and formatted only in the view layer.

## Phase 3: Add typed service boundaries

Create interfaces for all backend-facing behavior. Suggested contracts:

```ts
interface AuthService {
  signIn(input: SignInRequest): Promise<AuthSession>
  signOut(): Promise<void>
  restoreSession(): Promise<AuthSession | null>
  requestEmailVerification(email: string): Promise<void>
  verifyEmailCode(input: VerifyEmailCodeRequest): Promise<void>
  createAccount(input: CreateAccountRequest): Promise<AuthSession>
}

interface ConversationService {
  list(): Promise<ConversationSummary[]>
  get(id: string): Promise<Conversation>
  create(input: CreateConversationRequest): Promise<Conversation>
  rename(id: string, title: string): Promise<ConversationSummary>
  delete(id: string): Promise<void>
  updateConfiguration(
    id: string,
    input: UpdateConversationConfigurationRequest,
  ): Promise<Conversation>
}

interface MessageService {
  send(input: SendMessageRequest): Promise<ChatMessage>
  cancel(conversationId: string, messageId: string): Promise<void>
  retry(conversationId: string, messageId: string): Promise<ChatMessage>
}

interface SourceService {
  list(): Promise<SourceDocument[]>
  upload(files: File[]): Promise<SourceDocument[]>
  delete(id: string): Promise<void>
  getSummary(id: string): Promise<string[]>
}
```

Provide mock implementations with realistic delays and controllable failures. UI code must depend on the interfaces, not directly on mock modules.

Create an API client placeholder that centralizes:

- Base URL
- JSON serialization
- Authentication headers
- Request IDs
- Abort signals
- Error normalization
- HTTP status handling

Do not scatter `fetch()` calls through components.

## Phase 4: Add routing and session handling

Add explicit frontend routes such as:

```text
/login
/signup
/signup/email
/chat
/chat/:conversationId
/profile
/settings
/help
```

Implement:

- Authentication provider
- Session restoration
- Protected routes
- Redirect back to the requested page after login
- Logout cleanup
- Unknown-route page
- Loading state while restoring a session

Keep mock credentials temporarily, but move them into the mock authentication service. No component should compare credentials directly.

## Phase 5: Make workflows backend-ready

### Conversations

- Load and paginate the conversation list.
- Create separate conversations with stable mock server IDs.
- Rename with pending and error states.
- Delete with confirmation, pending state, error recovery, and predictable post-delete selection.
- Decide whether deleting the active chat selects the next chat or opens a new draft.
- Preserve unsent drafts per conversation.
- Support empty, loading, and failed list states.

### Messages

- Render user and assistant messages from service responses.
- Add pending, streaming, complete, stopped, and failed states.
- Disable duplicate sends while appropriate.
- Add cancel, retry, regenerate, and copy actions.
- Preserve message input when sending fails.
- Auto-scroll only when the user is already near the bottom.
- Support long conversations without rendering performance degradation.
- Render Markdown safely.
- Add code blocks, copy-code actions, and syntax highlighting if code responses are supported.

Mock streaming may use an async iterator or timed chunks, but its interface should be replaceable by SSE, WebSocket, or fetch streaming.

### Attachments and sources

- Connect the composer attachment input to frontend file state.
- Connect the Sources upload button.
- Validate file type, file size, count, duplicates, and empty files.
- Show upload and processing progress.
- Show preview, retry, remove, and failed states.
- Revoke object URLs when previews are removed.
- Keep source selection scoped to the active conversation or next message as specified.
- Replace native browser confirmation dialogs with the shared in-app dialog.

### System prompt and model configuration

- Store saved values per conversation.
- Maintain separate saved and draft values.
- Handle unsaved-change confirmation.
- Add pending and error states for saves.
- Define request DTOs now, even while using mock services.
- Keep Modelfile parsing as a frontend import feature, but validate encoding and size.

### Authentication and signup

- Move hardcoded email, code, and credentials into mock services.
- Add pending and server-error states.
- Add code resend, cooldown, and expiration UI.
- Add OAuth redirect placeholder contracts for Google and company SSO.
- Add forgot-password and reset-password route placeholders if these are required by the product.
- Do not store real tokens in source code.

### Inactive controls

Resolve every visible control, including:

- Dictation
- Voice Chat
- Profile
- Settings
- Help
- Google signup
- Company signup
- Source upload
- Composer attachments
- Temporary Chat behavior

If a feature is outside scope, disable the control and provide an accessible explanation rather than leaving it apparently functional.

## Phase 6: Standardize asynchronous state

Use a consistent state shape for server operations:

```ts
type AsyncStatus = "idle" | "pending" | "success" | "error"

interface AsyncState<T> {
  status: AsyncStatus
  data?: T
  error?: AppError
}
```

Normalize errors into categories such as:

- Validation
- Unauthorized
- Forbidden
- Not found
- Conflict
- Rate limited
- Offline
- Timeout
- Server error
- Unknown

Every mutation must define whether it is optimistic and how it rolls back.

## Phase 7: Accessibility and responsive completion

### Accessibility requirements

- Add a skip link and a stable main-content target.
- Verify every button has an accessible name.
- Use menu semantics for profile and conversation action menus.
- Support keyboard navigation through conversations.
- Announce message status and new assistant messages appropriately.
- Preserve focus when opening and closing dialogs.
- Verify Escape, backdrop, and close-button behavior.
- Add visible focus styles.
- Verify color contrast.
- Respect reduced-motion preferences.
- Run automated Axe checks, then perform a keyboard-only pass.

### Responsive requirements

Verify at minimum:

- 360 px phone
- 430 px phone
- 768 px tablet
- 1024 px laptop
- 1440 px desktop
- 200% browser zoom

Replace fixed side rails with accessible mobile drawers or menus where needed. Test the composer with an on-screen keyboard and long input. Test long titles, prompts, filenames, messages, and source lists.

## Phase 8: Testing

Add:

- Vitest
- React Testing Library
- `@testing-library/user-event`
- Mock Service Worker or an equivalent network-level mock
- Playwright or another supported end-to-end runner
- Axe integration

Required unit and component coverage:

- Domain mapping and date formatting
- Conversation reducer or state hooks
- Conversation isolation
- Message pending, success, streaming, and failure states
- Rename validation
- Delete confirmation and rollback
- System-prompt saved and draft behavior
- Source selection and file validation
- Login validation and session restoration
- Signup step transitions and error states
- Modal focus management

Required end-to-end coverage:

1. Sign in and sign out.
2. Restore a session after refresh.
3. Create, switch, rename, search, and delete conversations.
4. Delete the active conversation and immediately type into the new composer.
5. Delete all conversations and create another conversation.
6. Send a message and observe pending and completed states.
7. Recover from a failed message.
8. Save and reload a per-conversation system prompt.
9. Upload, select, and delete a source.
10. Verify conversation settings remain isolated.
11. Complete email signup with mocked success and failure responses.
12. Operate primary workflows using only the keyboard.

## Phase 9: Tooling and continuous integration

Add package scripts:

```json
{
  "scripts": {
    "dev": "vite --host 0.0.0.0",
    "build": "vite build",
    "preview": "vite preview",
    "format": "oxfmt",
    "format:check": "oxfmt --check .",
    "typecheck": "tsc --noEmit",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest",
    "test:e2e": "playwright test",
    "validate": "pnpm format:check && pnpm lint && pnpm typecheck && pnpm test && pnpm build"
  }
}
```

Add CI that installs with the lockfile and runs the validation command. Do not make CI depend on a real backend.

## Phase 10: Backend handoff documentation

Create or update the project README with:

- Supported Node.js and pnpm versions
- Installation and local-run instructions
- Environment variables
- Application routes
- Architecture overview
- Service-interface overview
- How to switch between mock and real services
- Authentication assumptions
- Streaming assumptions
- File-upload limits and accepted types
- Error response expectations
- Validation commands

Add `.env.example`, for example:

```dotenv
VITE_API_BASE_URL=http://localhost:3000/api
VITE_USE_MOCK_API=true
```

Document expected endpoints or provide an OpenAPI draft for:

- Authentication and session
- Conversations
- Messages and streaming
- Conversation configuration
- Sources and uploads
- Model availability

Include request, success, validation-error, authorization-error, and server-error examples.

## Final validation gate

Before declaring the frontend ready:

```bash
pnpm install --frozen-lockfile
pnpm format:check
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm build
```

Also complete:

- Keyboard-only walkthrough
- Screen-reader smoke test
- Automated accessibility scan
- Responsive viewport walkthrough
- Offline and slow-network simulation
- Backend mock failure simulation
- Refresh and deep-link testing
- Browser console error check

## Required final report from the implementing agent

At the end of the work, report:

1. Architecture and files added or moved.
2. Domain and API contracts introduced.
3. Mock services and how to replace them.
4. Completed and intentionally deferred controls.
5. Conversation-scoped state behavior.
6. Authentication and routing behavior.
7. Accessibility and responsive improvements.
8. Tests added and validation commands run.
9. Environment variables and setup steps.
10. Remaining backend assumptions or unresolved product decisions.

Do not label the project backend-ready while any critical control is silently inactive, conversation data leaks between chats, service calls remain embedded in UI components, or the required validation suite is failing.
