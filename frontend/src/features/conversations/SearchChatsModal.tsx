import type { Dispatch, RefObject, SetStateAction } from "react"
import { CenteredModal } from "../../components/CenteredModal"
import type { Conversation } from "./types"
import { formatConversationTime } from "./formatConversationTime"

export function SearchChatsModal({
  open,
  searchValue,
  setSearchValue,
  setSearchOpen,
  conversations,
  selectConversation,
  searchInputRef,
  searchButtonRef,
}: {
  open: boolean
  searchValue: string
  setSearchValue: Dispatch<SetStateAction<string>>
  setSearchOpen: Dispatch<SetStateAction<boolean>>
  conversations: Conversation[]
  selectConversation: (conversationId: string) => void
  searchInputRef: RefObject<HTMLInputElement | null>
  searchButtonRef: RefObject<HTMLButtonElement | null>
}) {
  if (!open) return null

  return (
    <CenteredModal
      ariaLabel="Search chats"
      initialFocusRef={searchInputRef}
      returnFocusRef={searchButtonRef}
      onRequestClose={() => {
        setSearchOpen(false)
        setSearchValue("")
      }}
    >
      {/* Search input row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "14px 16px",
          borderBottom:
            "1px solid color-mix(in srgb, var(--app-border) 72%, transparent)",
        }}
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          style={{ flexShrink: 0 }}
        >
          <circle cx="11" cy="11" r="7" stroke="#5b7392" strokeWidth="2" />
          <path
            d="m20 20-3-3"
            stroke="#5b7392"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
        <input
          ref={searchInputRef}
          value={searchValue}
          onChange={(e) => setSearchValue(e.target.value)}
          placeholder="Search chats…"
          aria-label="Search chats"
          style={{
            flex: 1,
            border: "none",
            background: "transparent",
            outline: "none",
            fontSize: 15,
            color: "var(--app-text)",
            fontFamily: "inherit",
          }}
        />
        <button
          type="button"
          aria-label="Close search"
          onClick={() => {
            setSearchOpen(false)
            setSearchValue("")
          }}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "var(--app-muted-strong)",
            padding: 4,
            display: "flex",
            alignItems: "center",
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path
              d="M18 6 6 18M6 6l12 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>
      {/* Results */}
      <div style={{ maxHeight: 340, overflowY: "auto", padding: "8px 8px" }}>
        {(searchValue
          ? conversations.filter((c) =>
              c.title.toLowerCase().includes(searchValue.toLowerCase()),
            )
          : conversations
        ).map((chat) => (
          <button
            key={chat.id}
            onClick={() => selectConversation(chat.id)}
            style={{
              width: "100%",
              textAlign: "left",
              padding: "10px 12px",
              borderRadius: 9,
              border: "none",
              background: "transparent",
              cursor: "pointer",
              fontSize: 14,
              color: "var(--app-text)",
              fontFamily: "inherit",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              transition: "background 0.12s",
            }}
            onMouseEnter={(e) =>
              (e.currentTarget.style.background =
                "color-mix(in srgb, var(--app-accent) 10%, transparent)")
            }
            onMouseLeave={(e) =>
              (e.currentTarget.style.background = "transparent")
            }
          >
            <span>{chat.title}</span>
            <span
              style={{
                fontSize: 11,
                color: "var(--app-muted-strong)",
                flexShrink: 0,
                marginLeft: 12,
              }}
            >
              {formatConversationTime(chat.updatedAt)}
            </span>
          </button>
        ))}
        {(searchValue
          ? conversations.filter((c) =>
              c.title.toLowerCase().includes(searchValue.toLowerCase()),
            )
          : conversations
        ).length === 0 && (
          <p
            style={{
              fontSize: 13,
              color: "var(--app-muted-strong)",
              textAlign: "center",
              padding: "20px 0",
            }}
          >
            {searchValue ? "No chats found" : "No conversations yet"}
          </p>
        )}
      </div>
    </CenteredModal>
  )
}
