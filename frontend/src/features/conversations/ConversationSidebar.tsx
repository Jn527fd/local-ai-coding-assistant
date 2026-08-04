import {
  useEffect,
  useRef,
  type Dispatch,
  type FormEvent,
  type KeyboardEvent,
  type RefObject,
  type SetStateAction,
} from "react"
import { LogoButton, SideIconBtn } from "../../components/ToolbarButtons"
import type { Conversation } from "./types"
import { formatConversationTime } from "./formatConversationTime"

export function ConversationSidebar({
  sidebarOpen,
  setSidebarOpen,
  startNewConversation,
  searchButtonRef,
  recentsButtonRef,
  profileButtonRef,
  setSearchOpen,
  setSearchValue,
  setRecentsOpen,
  setProfileMenuOpen,
  recentsOpen,
  searchValue,
  filteredChats,
  listLoading,
  listError,
  listTotal,
  hasMoreConversations,
  onLoadMoreConversations,
  onRetryConversationList,
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
  profileMenuOpen,
  profileDisplayName,
  profileId,
  profileAvatarUrl,
}: {
  sidebarOpen: boolean
  setSidebarOpen: Dispatch<SetStateAction<boolean>>
  startNewConversation: () => void
  searchButtonRef: RefObject<HTMLButtonElement | null>
  recentsButtonRef: RefObject<HTMLButtonElement | null>
  profileButtonRef: RefObject<HTMLButtonElement | null>
  setSearchOpen: Dispatch<SetStateAction<boolean>>
  setSearchValue: Dispatch<SetStateAction<string>>
  setRecentsOpen: Dispatch<SetStateAction<boolean>>
  setProfileMenuOpen: Dispatch<SetStateAction<boolean>>
  recentsOpen: boolean
  searchValue: string
  filteredChats: Conversation[]
  listLoading: boolean
  listError: string
  listTotal: number
  hasMoreConversations: boolean
  onLoadMoreConversations: () => void
  onRetryConversationList: () => void
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
  profileMenuOpen: boolean
  profileDisplayName: string
  profileId: string
  profileAvatarUrl: string | null
}) {
  const handleConversationKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return
    const buttons = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>(
        "[data-conversation-select]",
      ),
    )
    if (buttons.length === 0) return
    event.preventDefault()
    const currentIndex = buttons.indexOf(
      document.activeElement as HTMLButtonElement,
    )
    const nextIndex =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? buttons.length - 1
          : event.key === "ArrowDown"
            ? Math.min(buttons.length - 1, Math.max(0, currentIndex + 1))
            : Math.max(0, currentIndex <= 0 ? 0 : currentIndex - 1)
    buttons[nextIndex]?.focus()
  }

  return (
    <aside
      id="conversation-sidebar-content"
      className={`conversation-sidebar${sidebarOpen ? " is-open" : ""}`}
      aria-label="Conversation navigation"
      style={{
        position: "fixed",
        top: 0,
        left: 0,
        height: "100vh",
        width: sidebarOpen ? 260 : 56,
        background: "var(--app-surface)",
        backdropFilter: "blur(16px)",
        borderRight:
          "1px solid color-mix(in srgb, var(--app-border) 72%, transparent)",
        transition: "width 0.28s cubic-bezier(0.4,0,0.2,1)",
        display: "flex",
        flexDirection: "column",
        zIndex: 40,
        overflow: "hidden",
      }}
    >
      {/* Logo / toggle */}
      <div
        style={{
          height: 56,
          display: "flex",
          alignItems: "center",
          padding: "0 12px",
          borderBottom:
            "1px solid color-mix(in srgb, var(--app-border) 72%, transparent)",
          flexShrink: 0,
        }}
      >
        <LogoButton
          open={sidebarOpen}
          onToggle={() => setSidebarOpen((v) => !v)}
        />
        {sidebarOpen && (
          <span
            style={{
              marginLeft: 10,
              fontWeight: 700,
              fontSize: 15,
              color: "var(--app-text)",
              whiteSpace: "nowrap",
              letterSpacing: "-0.02em",
            }}
          >
            LocalChat
          </span>
        )}
      </div>

      {/* Collapsed icon buttons / expanded full sidebar */}
      {!sidebarOpen ? (
        <div
          className="menu-backdrop"
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 4,
            padding: "10px 0",
          }}
        >
          {/* New chat */}
          <SideIconBtn title="New Chat" onClick={startNewConversation}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 5v14M5 12h14"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
              />
            </svg>
          </SideIconBtn>
          {/* Search */}
          <SideIconBtn
            buttonRef={searchButtonRef}
            title="Search chats"
            onClick={() => setSearchOpen(true)}
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <circle
                cx="11"
                cy="11"
                r="7"
                stroke="currentColor"
                strokeWidth="1.9"
              />
              <path
                d="m20 20-3-3"
                stroke="currentColor"
                strokeWidth="1.9"
                strokeLinecap="round"
              />
            </svg>
          </SideIconBtn>
          {/* Recents */}
          <div style={{ position: "relative" }}>
            <SideIconBtn
              buttonRef={recentsButtonRef}
              title="Recent chats"
              active={recentsOpen}
              onClick={() => setRecentsOpen((v) => !v)}
              ariaHasPopup="menu"
              ariaExpanded={recentsOpen}
              ariaControls="recent-conversations-menu"
            >
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <path
                  d="M12 8v4l3 3"
                  stroke="currentColor"
                  strokeWidth="1.9"
                  strokeLinecap="round"
                />
                <circle
                  cx="12"
                  cy="12"
                  r="9"
                  stroke="currentColor"
                  strokeWidth="1.9"
                />
              </svg>
            </SideIconBtn>
          </div>
        </div>
      ) : (
        <>
          {/* New chat button */}
          <div style={{ padding: "10px 10px 6px" }}>
            <button
              type="button"
              onClick={startNewConversation}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                gap: 8,
                padding: "8px 10px",
                borderRadius: 10,
                border:
                  "1px solid color-mix(in srgb, var(--app-accent) 38%, transparent)",
                background:
                  "color-mix(in srgb, var(--app-accent) 12%, transparent)",
                cursor: "pointer",
                color: "var(--app-accent)",
                fontWeight: 600,
                fontSize: 13,
                whiteSpace: "nowrap",
                transition: "background 0.15s",
              }}
              onMouseEnter={(e) =>
                (e.currentTarget.style.background = "rgba(79,142,247,0.16)")
              }
              onMouseLeave={(e) =>
                (e.currentTarget.style.background = "rgba(79,142,247,0.08)")
              }
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                style={{ flexShrink: 0 }}
              >
                <path
                  d="M12 5v14M5 12h14"
                  stroke="#3b6fd4"
                  strokeWidth="2.2"
                  strokeLinecap="round"
                />
              </svg>
              New Chat
            </button>
          </div>
          {/* Search */}
          <div style={{ padding: "0 10px 6px" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                background: "var(--app-surface-soft)",
                border:
                  "1px solid color-mix(in srgb, var(--app-border) 74%, transparent)",
                borderRadius: 9,
                padding: "7px 10px",
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                <circle
                  cx="11"
                  cy="11"
                  r="7"
                  stroke="#5b7392"
                  strokeWidth="2"
                />
                <path
                  d="m20 20-3-3"
                  stroke="#5b7392"
                  strokeWidth="2"
                  strokeLinecap="round"
                />
              </svg>
              <input
                value={searchValue}
                onChange={(e) => setSearchValue(e.target.value)}
                aria-label="Filter conversation history"
                placeholder="Search chats…"
                style={{
                  border: "none",
                  background: "transparent",
                  outline: "none",
                  fontSize: 12,
                  color: "var(--app-text)",
                  width: "100%",
                }}
              />
            </div>
          </div>
          {/* Recent chats list */}
          <div
            className="conversation-history"
            aria-label="Conversation history"
            onKeyDown={handleConversationKeyDown}
            style={{ flex: 1, overflowY: "auto", padding: "4px 10px" }}
          >
            <p
              style={{
                fontSize: 10,
                fontWeight: 700,
                color: "#5f7390",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                margin: "6px 2px 8px",
              }}
            >
              Recent
            </p>
            {filteredChats.map((chat) => (
              <div
                className={`conversation-list-row ${
                  activeConversationId === chat.id ? "is-active" : ""
                }`}
                key={chat.id}
              >
                {editingConversationId === chat.id ? (
                  <form
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
                      aria-label="Save conversation name"
                      title="Save name"
                      disabled={
                        !editingConversationTitle.trim() ||
                        renamingConversationId === chat.id
                      }
                    >
                      <span aria-hidden="true">
                        {renamingConversationId === chat.id ? "…" : "✓"}
                      </span>
                    </button>
                    <button
                      type="button"
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
                      data-conversation-select
                      className="conversation-select-button"
                      type="button"
                      onClick={() => selectConversation(chat.id)}
                      aria-current={
                        activeConversationId === chat.id ? "page" : undefined
                      }
                    >
                      <span className="conversation-title">{chat.title}</span>
                      <span className="conversation-time">
                        {formatConversationTime(chat.updatedAt)}
                      </span>
                    </button>
                    <button
                      className="conversation-rename-button"
                      type="button"
                      aria-label={`Rename ${chat.title}`}
                      title="Rename conversation"
                      onClick={() => startRenamingConversation(chat)}
                    >
                      <span aria-hidden="true">✎</span>
                    </button>
                    <button
                      className="conversation-delete-button"
                      type="button"
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
            {filteredChats.length === 0 && (
              <p className="conversation-empty-state">
                {listLoading
                  ? "Loading conversations…"
                  : listError
                    ? "Conversations could not be loaded"
                    : searchValue
                      ? "No chats found"
                      : "No conversations yet"}
              </p>
            )}
            {conversationActionError && (
              <p className="conversation-list-error" role="alert">
                {conversationActionError}
              </p>
            )}
            {listError && filteredChats.length > 0 && (
              <p className="conversation-list-error" role="alert">
                {listError}
              </p>
            )}
            {listError && (
              <button
                type="button"
                className="conversation-load-more"
                onClick={onRetryConversationList}
                disabled={listLoading}
              >
                Retry loading conversations
              </button>
            )}
            {hasMoreConversations && !searchValue && (
              <button
                type="button"
                className="conversation-load-more"
                onClick={onLoadMoreConversations}
                disabled={listLoading}
              >
                {listLoading
                  ? "Loading…"
                  : `Load more (${filteredChats.length} of ${listTotal})`}
              </button>
            )}
          </div>
        </>
      )}

      {/* Profile */}
      <button
        ref={profileButtonRef}
        type="button"
        onClick={() => {
          setProfileMenuOpen((open) => !open)
          setRecentsOpen(false)
        }}
        aria-expanded={profileMenuOpen}
        aria-haspopup="menu"
        aria-controls="profile-menu"
        aria-label="Open profile menu"
        style={{
          width: "100%",
          border: "none",
          borderTop: "1px solid rgba(200,220,255,0.4)",
          marginTop: "auto",
          padding: "10px 12px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          flexShrink: 0,
          background: "transparent",
          cursor: "pointer",
          fontFamily: "inherit",
        }}
      >
        <span
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            overflow: "hidden",
            background:
              "linear-gradient(145deg, color-mix(in srgb, var(--app-accent) 18%, white), color-mix(in srgb, var(--app-accent-2) 16%, white))",
            display: "grid",
            placeItems: "center",
            flexShrink: 0,
            fontSize: 11,
            fontWeight: 800,
            color: "var(--app-text-strong)",
            boxShadow:
              "0 0 0 1px color-mix(in srgb, var(--app-border) 70%, transparent), 0 4px 12px rgba(52, 92, 145, 0.12)",
          }}
        >
          {profileAvatarUrl ? (
            <img
              src={profileAvatarUrl}
              alt=""
              style={{ width: "100%", height: "100%", objectFit: "cover" }}
            />
          ) : (
            <span aria-hidden="true">
              {profileDisplayName
                .split(/\s+/)
                .slice(0, 2)
                .map((part) => part[0])
                .join("")
                .toUpperCase() || "U"}
            </span>
          )}
        </span>

        {sidebarOpen && (
          <span style={{ display: "block", textAlign: "left" }}>
            <span
              style={{
                display: "block",
                fontSize: 13,
                fontWeight: 600,
                color: "var(--app-text)",
              }}
            >
              {profileDisplayName || "User"}
            </span>

            <span
              style={{
                display: "block",
                fontSize: 11,
                color: "var(--app-muted-strong)",
              }}
            >
              {profileId || "user-local"}
            </span>
          </span>
        )}
      </button>
    </aside>
  )
}

export function ProfileMenu({
  profileMenuOpen,
  setProfileMenuOpen,
  sidebarOpen,
  onNavigate,
  handleLogout,
  profileButtonRef,
}: {
  profileMenuOpen: boolean
  setProfileMenuOpen: Dispatch<SetStateAction<boolean>>
  sidebarOpen: boolean
  onNavigate: (
    path: "/profile" | "/repositories" | "/diagnostics" | "/settings" | "/help",
  ) => void
  handleLogout: () => void
  profileButtonRef: RefObject<HTMLButtonElement | null>
}) {
  const menuRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (!profileMenuOpen) return
    const profileButton = profileButtonRef.current
    const frame = window.requestAnimationFrame(() => {
      menuRef.current
        ?.querySelector<HTMLButtonElement>("[role='menuitem']")
        ?.focus()
    })
    const handleEscape = (event: globalThis.KeyboardEvent) => {
      if (event.key !== "Escape") return
      event.preventDefault()
      setProfileMenuOpen(false)
    }
    document.addEventListener("keydown", handleEscape)
    return () => {
      window.cancelAnimationFrame(frame)
      document.removeEventListener("keydown", handleEscape)
      profileButton?.focus()
    }
  }, [profileButtonRef, profileMenuOpen, setProfileMenuOpen])

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return
    const items = Array.from(
      event.currentTarget.querySelectorAll<HTMLButtonElement>(
        "[role='menuitem']",
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
      {profileMenuOpen && (
        <div
          onClick={() => {
            setProfileMenuOpen(false)
          }}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 50,
          }}
        >
          <div
            id="profile-menu"
            ref={menuRef}
            role="menu"
            aria-label="Account menu"
            className="profile-menu-panel"
            onKeyDown={handleMenuKeyDown}
            onClick={(event) => event.stopPropagation()}
            style={{
              position: "fixed",
              bottom: 12,
              left: sidebarOpen ? 266 : 62,
              width: 200,
              padding: "6px",
              background: "var(--app-surface)",
              backdropFilter: "blur(16px)",
              border:
                "1px solid color-mix(in srgb, var(--app-border) 72%, transparent)",
              borderRadius: 12,
              boxShadow: "var(--app-shadow)",
              zIndex: 51,
            }}
          >
            {[
              "Profile",
              "Repositories",
              "Diagnostics",
              "Settings",
              "Help",
              "Log out",
            ].map((option) => (
              <button
                key={option}
                type="button"
                role="menuitem"
                onClick={() => {
                  if (option === "Log out") handleLogout()
                  else {
                    setProfileMenuOpen(false)
                    onNavigate(
                      `/${option.toLowerCase()}` as "/profile" | "/repositories" | "/diagnostics" | "/settings" | "/help",
                    )
                  }
                }}
                style={{
                  width: "100%",
                  display: "block",
                  padding: "9px 12px",
                  border: "none",
                  borderRadius: 8,
                  background: "transparent",
                  color: option === "Log out" ? "#dc4c4c" : "var(--app-text)",
                  fontSize: 13,
                  fontFamily: "inherit",
                  textAlign: "left",
                  cursor: "pointer",
                }}
                onMouseEnter={(event) => {
                  event.currentTarget.style.background = "rgba(79,142,247,0.08)"
                }}
                onMouseLeave={(event) => {
                  event.currentTarget.style.background = "transparent"
                }}
              >
                {option}
              </button>
            ))}
          </div>
        </div>
      )}
    </>
  )
}
