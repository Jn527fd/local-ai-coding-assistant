# Phase 2 completion report

Date: July 18, 2026

## Status

Phase 2 is complete. The prototype now uses explicit frontend domain models and conversation-owned configuration instead of inferring shapes from mock arrays or keeping conversation settings in global UI state.

Phase 3 has not started. No service interfaces, mock service implementations, API client, HTTP behavior, or asynchronous service boundary was added.

## Domain models

`src/domain/models.ts` now defines:

- `MessageRole`
- `MessageStatus`
- `AttachmentStatus`
- `ChatAttachment`
- `ChatMessage`
- `ModelConfiguration`
- `Conversation`
- `SourceDocumentStatus`
- `SourceDocument`
- `ConversationDraftConfiguration`

Each message now carries its conversation ID, status, ISO creation timestamp, and typed attachment list. Each conversation carries ISO creation and update timestamps, messages, system prompt, model configuration, selected source IDs, and its temporary-chat flag.

## DTO definitions

`src/domain/dtos.ts` defines request DTOs separately from frontend state:

- `CreateConversationRequestDto`
- `RenameConversationRequestDto`
- `UpdateConversationConfigurationRequestDto`
- `SendMessageRequestDto`

It also defines explicit response DTOs for conversations, messages, and source documents. These definitions establish backend-mappable shapes without introducing the Phase 3 service layer.

## Conversation isolation

The former global prompt, model, source-selection, and temporary-chat states were removed from `App.tsx`.

The active values are now read from the selected `Conversation`. Updates write back only to that conversation. When no conversation exists yet, a typed draft configuration is used and transferred into the conversation created by the first message. Starting a new conversation creates clean default configuration.

This means:

- Saving a system prompt affects only the selected conversation.
- Changing any model option affects only the selected conversation.
- Selecting or clearing sources affects only the selected conversation.
- Temporary-chat state belongs to the selected conversation.
- Switching conversations restores the selected conversation's configuration.
- Deleting a source removes its ID from every conversation so stale references are not retained.

## Timestamp handling

- Conversation and message timestamps are stored as ISO strings.
- Mock source creation times are explicit ISO strings.
- Conversation timestamps are formatted only in the conversation list and search views.
- Source timestamps and file sizes are formatted only inside the Sources view.
- Static display fields such as `time: "Now"` and mock metadata strings were removed from stored data.

## Files changed

Added:

- `src/domain/models.ts`
- `src/domain/dtos.ts`
- `src/domain/defaults.ts`
- `src/features/conversations/formatConversationTime.ts`
- `docs/PHASE_2_COMPLETION.md`

Updated:

- `src/App.tsx`
- `src/features/configuration/ChatConfigurationModal.tsx`
- `src/features/configuration/RightConfigurationToolbar.tsx`
- `src/features/conversations/ConversationSidebar.tsx`
- `src/features/conversations/SearchChatsModal.tsx`
- `src/features/conversations/types.ts`
- `src/features/sources/SourcesModal.tsx`
- `docs/PHASE_1_COMPLETION.md`

## Browser verification

A two-conversation isolation scenario was exercised in the running application:

1. Conversation Alpha was created.
2. Its prompt was set to `Alpha-only prompt`.
3. Its LLM was changed to `mistral:7b`.
4. `Product-Roadmap.pdf` was selected.
5. Temporary-chat mode was enabled.
6. A new conversation was created and showed an empty prompt, the default `llama3.2:3b` model, zero selected sources, and no temporary-chat banner.
7. Switching back to Conversation Alpha restored its prompt, `mistral:7b`, selected source, temporary-chat banner, and original messages.

The existing login, message submission, generic response, new-chat notice, sidebar, modal, and source-list behaviors remained operational during this scenario.

## Automated validation

The following commands completed successfully using the configured workspace Node runtime:

```powershell
.\node_modules\.bin\oxfmt.cmd src
.\node_modules\.bin\tsc.cmd --noEmit
pnpm run build
git diff --check
```

Production build result:

- Vite 8.0.3
- 31 modules transformed
- JavaScript bundle: 252.63 kB (74.50 kB gzip)
- CSS bundle: 30.86 kB (6.97 kB gzip)
- Build completed successfully

The repository still has no lint command or automated test suite, so neither was available to run. This limitation remains documented and was not addressed because it is outside the approved Phase 2 scope.

## Phase boundary

Phase 2 was reviewed and explicitly approved by the user before Phase 3 began.
