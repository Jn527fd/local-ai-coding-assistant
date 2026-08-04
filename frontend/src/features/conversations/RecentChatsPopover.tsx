import {
  useEffect,
  useRef,
  type Dispatch,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
  type SetStateAction,
} from "react"
import type { Conversation } from "./types"

export function RecentChatsPopover({
  recentsOpen,
  setRecentsOpen,
  conversations,
  activeConversationId,
  selectConversation,
  editingConversationId,
  saveConversationName,
  editingConversationTitle,
  renamingConversationId,
  conversationActionError,
  setEditingConversationTitle,
  cancelRenamingConversation,
  startRenamingConversation,
  requestDeleteConversation,
  recentsButtonRef,
}: {
  recentsOpen: boolean
  setRecentsOpen: Dispatch<SetStateAction<boolean>>
  conversations: Conversation[]
  activeConversationId: string | null
  selectConversation: (conversationId: string) => void
  editingConversationId: string | null
  saveConversationName: (
    event: FormEvent<HTMLFormElement>,
    conversationId: string,
  ) => void
  editingConversationTitle: string
  renamingConversationId: string | null
  conversationActionError: string
  setEditingConversationTitle: Dispatch<SetStateAction<string>>
  cancelRenamingConversation: () => void
  startRenamingConversation: (conversation: Conversation) => void
  requestDeleteConversation: (conversationId: string) => void
  recentsButtonRef: RefObject<HTMLButtonElement | null>
}) {
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!recentsOpen) return
    const recentsButton = recentsButtonRef.current
    const frame = window.requestAnimationFrame(() => {
      menuRef.current
        ?.querySelector<HTMLButtonElement>("[role='menuitem']")
        ?.focus()
    })
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return
      event.preventDefault()
      setRecentsOpen(false)
    }
    document.addEventListener("keydown", handleEscape)
    return () => {
      window.cancelAnimationFrame(frame)
      document.removeEventListener("keydown", handleEscape)
      recentsButton?.focus()
    }
  }, [recentsButtonRef, recentsOpen, setRecentsOpen])

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>(
        "[role='menuitem']:not(:disabled)",
      ),
    )
    if (items.length === 0) return
    event.preventDefault()
    const index = items.indexOf(document.activeElement as HTMLButtonElement)
    const nextIndex =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? items.length - 1
          : event.key === "ArrowDown"
            ? (index + 1 + items.length) % items.length
            : (index - 1 + items.length) % items.length
    items[nextIndex]?.focus()
  }

  return (
    <>
      {recentsOpen && (
        <div
          className="menu-backdrop"
          onClick={() => setRecentsOpen(false)}
          style={{ position: "fixed", inset: 0, zIndex: 50 }}
        >
          <div
            id="recent-conversations-menu"
            ref={menuRef}
            role="menu"
            aria-label="Recent conversations"
            className="recent-conversations-panel"
            onKeyDown={handleMenuKeyDown}
            onClick={(e) => e.stopPropagation()}
            style={{
              position: "fixed",
              top: 120,
              left: 62,
              width: 220,
              background: "var(--app-surface)",
              backdropFilter: "blur(16px)",
              border:
                "1px solid color-mix(in srgb, var(--app-border) 72%, transparent)",
              borderRadius: 12,
              boxShadow: "var(--app-shadow)",
              overflow: "hidden",
              zIndex: 51,
            }}
          >
            <p
              role="presentation"
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: "var(--app-muted-strong)",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                padding: "10px 12px 4px",
              }}
            >
              Recent
            </p>
            {conversations.map((chat) => (
              <div
                role="presentation"
                className={`conversation-list-row conversation-list-row-compact ${
                  activeConversationId === chat.id ? "is-active" : ""
                }`}
                key={chat.id}
              >
                {editingConversationId === chat.id ? (
                  <form
                    role="presentation"
                    className="conversation-rename-form"
                    onSubmit={(event) => saveConversationName(event, chat.id)}
                  >
                    <input
                      autoFocus
                      aria-label="Conversation name"
                      value={editingConversationTitle}
                      onChange={(event) =>
                        setEditingConversationTitle(event.target.value)
                      }
                      onKeyDown={(event) => {
                        if (event.key === "Escape") {
                          event.preventDefault()
                          cancelRenamingConversation()
                        }
                      }}
                    />
                    <button
                      type="submit"
                      role="menuitem"
                      aria-label="Save conversation name"
                      title="Save name"
                      disabled={
                        !editingConversationTitle.trim() ||
                        renamingConversationId === chat.id
                      }
                    >
                      <span aria-hidden="true">✓</span>
                    </button>
                    <button
                      type="button"
                      role="menuitem"
                      aria-label="Cancel renaming"
                      title="Cancel"
                      onClick={cancelRenamingConversation}
                    >
                      <span aria-hidden="true">×</span>
                    </button>
                  </form>
                ) : (
                  <>
                    <button
                      className="conversation-select-button"
                      type="button"
                      role="menuitem"
                      onClick={() => selectConversation(chat.id)}
                    >
                      <span className="conversation-title">{chat.title}</span>
                    </button>
                    <button
                      className="conversation-rename-button"
                      type="button"
                      role="menuitem"
                      aria-label={`Rename ${chat.title}`}
                      title="Rename conversation"
                      onClick={() => startRenamingConversation(chat)}
                    >
                      <span aria-hidden="true">✎</span>
                    </button>
                    <button
                      className="conversation-delete-button"
                      type="button"
                      role="menuitem"
                      aria-label={`Delete ${chat.title}`}
                      title="Delete conversation"
                      onClick={() => requestDeleteConversation(chat.id)}
                    >
                      <svg
                        width="15"
                        height="15"
                        viewBox="0 0 24 24"
                        fill="none"
                      >
                        <path
                          d="M4 7h16M9 7V4h6v3m-8 0 1 13h8l1-13M10 11v5m4-5v5"
                          stroke="currentColor"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        />
                      </svg>
                    </button>
                  </>
                )}
              </div>
            ))}
            {conversations.length === 0 && (
              <p className="conversation-empty-state" role="presentation">
                No conversations yet
              </p>
            )}
            {conversationActionError && (
              <div role="presentation">
                <p className="conversation-list-error" role="alert">
                  {conversationActionError}
                </p>
              </div>
            )}
            <div role="presentation" style={{ height: 6 }} />
          </div>
        </div>
      )}
    </>
  )
}
