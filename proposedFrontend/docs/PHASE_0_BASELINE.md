# Phase 0 Baseline Report

**Project:** LocalChat frontend prototype  
**Baseline date:** July 18, 2026  
**Branch:** `main`  
**Baseline commit:** `f98a7b9`  
**Status:** Agent verification complete; user approval pending  
**Phase 1:** Not started

## 1. Phase 0 scope

This phase records the current repository and product behavior before structural refactoring begins.

Phase 0 includes:

- Repository and tooling baseline
- Existing validation commands
- Current visible screens and important UI states
- Control and workflow inventory
- Current mock behavior
- Known defects and integration gaps

No application architecture, components, styling, or runtime behavior were changed during this phase.

## 2. Repository baseline

### Runtime observed

- Node.js: `v24.14.0`
- pnpm: `11.9.0`
- React: `19.x`
- Vite: `8.x`
- TypeScript: strict mode enabled
- Default local port: `8443`

### Current source shape

- `src/App.tsx`: 3,365 lines
- `src/index.css`: 1,618 lines
- `src/main.tsx`: React entry point
- `vite.config.ts`: Vite, Tailwind, and Figma Make configuration
- `run-local.sh`: local dependency and development-server helper
- `FRONTEND_HANDOFF_GUIDE.md`: frontend-readiness execution guide

The product implementation is concentrated primarily in `src/App.tsx` and `src/index.css`.

### Working-tree state at baseline

The repository already contained user-owned or previously created changes. They were preserved.

```text
M  src/App.tsx
M  src/index.css
?? .figma/
?? FRONTEND_HANDOFF_GUIDE.md
?? dist/
?? node_modules/
?? run-local.sh
```

The Phase 0 report itself adds `docs/PHASE_0_BASELINE.md`.

## 3. Validation results

| Check | Command | Result | Notes |
| --- | --- | --- | --- |
| Dependency installation | `pnpm install --frozen-lockfile` | Pass | Lockfile and installed dependencies are current. |
| Guide format command | `pnpm format -- --check` | Fail | The script forwards an extra `--` and no target files to oxfmt. This is a command/tooling gap, not a source-formatting failure. |
| Direct source format check | `node_modules/.bin/oxfmt --check src/App.tsx src/index.css` | Pass | Both current source files are formatted. |
| Guide TypeScript command | `pnpm exec tsc --noEmit` | Fail in the current Windows agent shell | The `tsc` command shim was not resolved by `pnpm exec`. |
| Direct TypeScript check | `node_modules/.bin/tsc --noEmit` | Pass | Strict TypeScript compilation succeeds. |
| Production build | `pnpm build` | Pass | Vite production output completed successfully. |
| Whitespace check | `git diff --check` | Pass | Git reports only expected LF-to-CRLF conversion warnings for the two modified source files. |
| Lint | Not available | Not run | No lint script or ESLint dependency exists. |
| Automated tests | Not available | Not run | No unit, component, accessibility, or end-to-end test framework exists. |

### Production build output observed

```text
dist/robots.txt
dist/index.html
dist/assets/index-BM2bv_fp.css
dist/assets/index-CJWOIfR5.js
```

The exact hashed asset names can change with later builds.

## 4. Important UI states inspected

The following states were inspected in the running application through the local preview:

1. Login screen with disabled and enabled Sign In states
2. Signup method selection screen
3. Google signup placeholder state
4. Initial authenticated empty-chat state
5. Simulated user and assistant conversation state
6. Expanded conversation sidebar
7. Profile popup menu
8. Chat Configuration modal
9. Context / System Prompt modal
10. Sources modal with the seeded mock documents

Previously implemented conversation deletion focus behavior and the in-app delete confirmation modal remain part of the current baseline.

No screenshots were captured. The baseline records semantic behavior and visible control states in text.

## 5. Screen and workflow inventory

### Authentication

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Username field | Working mock | Accepts local input. |
| Password field | Working mock | Uses a masked password input. |
| Sign In | Working mock | Only `test` / `test` succeeds. |
| Invalid login error | Working mock | Displays an inline error. |
| Session persistence | Missing | Authentication resets on refresh. |
| Sign Up navigation | Working locally | Uses component state rather than routes. |
| Logout | Working locally | Clears local authentication state. |

### Signup

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Signup method screen | Working visually | Shows email, Google, and company choices. |
| Email signup | Working mock | Only `test@email.com` proceeds. |
| Verification code | Working mock | Only `12345` proceeds. |
| Password requirements | Working locally | Validates length, upper/lowercase, number, special character, and matching passwords. |
| Account-created state | Working mock | Continues directly into the local app. |
| Google signup | Placeholder | Displays a visual-placeholder message. |
| Company signup | Placeholder | Displays a visual-placeholder message. |
| Email delivery, resend, expiry | Missing | No provider, timer, resend, or expiry state exists. |

### Conversation sidebar

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Expand and collapse sidebar | Working locally | Changes the sidebar width and labels. |
| New Chat | Working locally | Creates an in-memory conversation and displays a notification. |
| Conversation list | Working locally | Displays current in-memory conversations. |
| Conversation selection | Working locally | Loads the selected conversation's messages. |
| Sidebar search | Working locally | Filters the in-memory conversation list. |
| Search Chats modal | Working locally | Searches and selects in-memory conversations. |
| Recent Chats popup | Working locally | Displays compact in-memory conversation controls. |
| Rename conversation | Working locally | Provides an inline editor with save and cancel behavior. |
| Delete conversation | Working locally | Uses an in-app confirmation modal. |
| Empty conversation list | Working locally | Shows “No conversations yet.” |
| Persistence | Missing | Conversations reset on refresh. |
| Pagination | Missing | All conversations are rendered together. |

### Chat and composer

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Empty chat state | Working visually | Shows the LocalChat empty-state prompt. |
| Text composer | Working locally | Accepts input and sends on Enter. |
| Send button | Working mock | Creates a user message and immediate generic assistant response. |
| Message transcript | Working visually | Displays user and assistant message bubbles. |
| New chat after deleting active chat | Working in current baseline | The in-app deletion modal returns focus to the composer. |
| Attach button | Incomplete | Opens the file chooser, but selected files are not processed or displayed. |
| Dictation | Inactive | Visible button has no action. |
| Voice Chat | Inactive | Empty-composer button calls the send handler, which exits because there is no text. |
| Streaming | Missing | Assistant response appears synchronously. |
| Pending/error/retry states | Missing | Message sending cannot fail or retry. |
| Markdown and code rendering | Missing | Messages render as plain paragraphs. |
| Draft preservation | Missing | Drafts are not stored per conversation. |

### Profile menu

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Profile menu open/close | Working visually | Opens above the bottom-left profile control. |
| Profile | Inactive | Closes the menu only. |
| Settings | Inactive | Closes the menu only. |
| Help | Inactive | Closes the menu only. |
| Log out | Working locally | Returns to the login screen. |

### Right toolbar and conversation configuration

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Temporary Chat | Visual-only | Toggles an indicator but does not change storage behavior. |
| Chat Configuration modal | Working visually | Provides local selects for eight model/tool categories. |
| LLM Model | Working local state | Selection is not sent anywhere. |
| Vision Model | Working local state | Selection is not sent anywhere. |
| Embedding Model | Working local state | Selection is not sent anywhere. |
| OCR Engine | Working local state | Selection is not sent anywhere. |
| PDF Parser | Working local state | Selection is not sent anywhere. |
| Vector Database | Working local state | Selection is not sent anywhere. |
| Context Compressor | Working local state | Selection is not sent anywhere. |
| ReRanker | Working local state | Selection is not sent anywhere. |
| Conversation isolation | Missing | Model values are global React state rather than conversation-owned data. |

### Context / System Prompt

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Centered modal | Working | Includes focus trapping, Escape, backdrop, and close behavior. |
| Prompt textarea | Working locally | Supports editing, placeholder text, scrolling, and character count. |
| Save Prompt | Working mock | Uses a short artificial delay and saves only in component state. |
| Clear Prompt | Working locally | Uses native browser confirmation for a saved prompt. |
| Unsaved-change warning | Working locally | Uses native browser confirmation. |
| Modelfile import | Working locally | Reads a text file smaller than 1 MB into the textarea. |
| Conversation isolation | Missing | The saved prompt is global state and is not loaded from each selected conversation. |
| LLM request inclusion | Missing | The prompt is not included in the generic mock response pipeline. |

### Sources

| Control or workflow | Current status | Current behavior |
| --- | --- | --- |
| Sources modal | Working visually | Uses the shared centered modal pattern. |
| Seeded source list | Mock | Five hardcoded documents are shown. |
| Source search | Working locally | Filters by filename. |
| Select source | Working locally | Maintains a local selected-ID set. |
| Select all / clear | Working locally | Updates local selection. |
| Quick summary | Mock | Displays hardcoded summary bullets. |
| Delete source | Working locally | Removes the mock document after native browser confirmation. |
| Upload document | Inactive | The empty-state upload button has no action. |
| Upload progress and processing | Missing | No file lifecycle exists. |
| Message integration | Missing | Selected sources are not included in message creation. |
| Conversation isolation | Missing | Selected sources are not stored on individual conversations. |

## 6. Current data and state behavior

### In-memory only

The following state resets on refresh:

- Authentication
- Signup progress
- Conversations
- Messages
- Conversation titles
- System prompt
- Model configuration
- Source collection changes
- Selected sources
- Temporary Chat selection

### Conversation model

The current conversation model contains only:

- ID
- Title
- Display time
- Messages

It does not contain timestamps, system prompt, model configuration, source IDs, owner, temporary status, pagination data, or backend synchronization status.

### Mock response behavior

Every sent message immediately produces the same generic assistant response. There are no asynchronous request, streaming, error, cancellation, or retry states.

## 7. Known defects and handoff gaps

### Critical integration gaps

1. No service or API boundary exists.
2. No routes or route-level authentication guard exist.
3. Authentication and signup credentials are hardcoded in UI logic.
4. Conversation configuration is not conversation-scoped.
5. No persistence or session restoration exists.
6. No loading, network-error, retry, rollback, or streaming states exist.
7. Attachments and source uploads are not implemented.
8. Several advertised controls are inactive.

### Maintainability gaps

1. Most application behavior lives in a 3,365-line component.
2. Styling is divided between a large global stylesheet and extensive inline style objects.
3. No reusable API types or DTOs exist.
4. Mock source types are inferred from the mock data array.
5. Display time uses static strings such as `Now` rather than stored timestamps.
6. Conversation IDs use `Date.now()` and are not server-compatible identifiers.

### Quality and delivery gaps

1. No lint configuration or lint command exists.
2. No automated tests exist.
3. No accessibility test tooling exists.
4. No end-to-end test runner exists.
5. No CI validation workflow exists.
6. No `.env.example` or API base URL configuration exists.
7. No frontend/backend contract documentation exists yet.
8. The current format and TypeScript commands need cross-platform package scripts.

### Responsive and accessibility risks requiring later verification

1. The desktop shell uses fixed left and right rails.
2. The composer and transcript use viewport calculations around those rails.
3. Mobile behavior has CSS breakpoints but has not received a complete phone/tablet interaction pass.
4. Sidebar and popup menu semantics need review.
5. Message updates do not yet expose meaningful streaming or error announcements.
6. Automated color-contrast and Axe checks are unavailable.

## 8. Phase 0 acceptance checklist

- [x] Repository state recorded
- [x] Runtime versions recorded
- [x] Source shape recorded
- [x] Existing changes preserved
- [x] Dependency installation verified
- [x] Source formatting verified through the direct formatter command
- [x] Strict TypeScript compilation verified through the direct command shim
- [x] Production build verified
- [x] Visible screens and important states inventoried
- [x] Working, mocked, inactive, and missing controls identified
- [x] Known defects and handoff gaps recorded
- [x] No Phase 1 refactoring performed
- [x] User has reviewed and approved the Phase 0 baseline

## 9. Phase gate

Phase 0 was reviewed and explicitly approved by the user before Phase 1 began.
