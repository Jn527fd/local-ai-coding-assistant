import { createRef } from "react"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import type { Conversation } from "./types"
import { ConversationSidebar, ProfileMenu } from "./ConversationSidebar"

const conversation: Conversation = {
  id: "chat-1",
  title: "Persisted chat",
  createdAt: "2026-07-20T12:00:00.000Z",
  updatedAt: "2026-07-20T12:00:00.000Z",
  messages: [],
  systemPrompt: "",
  modelConfiguration: { llmModel: "qwen3:4b", visionModel: "none" },
  sourceIds: [],
  temporary: false,
}

describe("ConversationSidebar", () => {
  it("renders persisted conversations and exposes list actions", async () => {
    const user = userEvent.setup()
    const selectConversation = vi.fn()
    const requestDeleteConversation = vi.fn()
    const onLoadMoreConversations = vi.fn()

    render(
      <ConversationSidebar
        sidebarOpen={true}
        setSidebarOpen={() => undefined}
        startNewConversation={() => undefined}
        searchButtonRef={createRef<HTMLButtonElement>()}
        recentsButtonRef={createRef<HTMLButtonElement>()}
        profileButtonRef={createRef<HTMLButtonElement>()}
        setSearchOpen={() => undefined}
        setSearchValue={() => undefined}
        setRecentsOpen={() => undefined}
        setProfileMenuOpen={() => undefined}
        recentsOpen={false}
        searchValue=""
        filteredChats={[conversation]}
        listLoading={false}
        listError=""
        listTotal={2}
        hasMoreConversations={true}
        onLoadMoreConversations={onLoadMoreConversations}
        onRetryConversationList={() => undefined}
        activeConversationId={null}
        selectConversation={selectConversation}
        editingConversationId={null}
        saveConversationName={() => undefined}
        editingConversationTitle=""
        renamingConversationId={null}
        conversationActionError=""
        setEditingConversationTitle={() => undefined}
        cancelRenamingConversation={() => undefined}
        startRenamingConversation={() => undefined}
        requestDeleteConversation={requestDeleteConversation}
        profileMenuOpen={false}
        profileDisplayName="Test User"
        profileId="user-local"
        profileAvatarUrl={null}
      />,
    )

    await user.click(screen.getByText("Persisted chat").closest("button")!)
    await user.click(
      screen.getByRole("button", { name: /Delete Persisted chat/ }),
    )
    await user.click(screen.getByRole("button", { name: /Load more/ }))

    expect(selectConversation).toHaveBeenCalledWith("chat-1")
    expect(requestDeleteConversation).toHaveBeenCalledWith("chat-1")
    expect(onLoadMoreConversations).toHaveBeenCalledOnce()
  })

  it("navigates account menu destinations and logs out explicitly", async () => {
    const user = userEvent.setup()
    const setProfileMenuOpen = vi.fn()
    const onNavigate = vi.fn()
    const handleLogout = vi.fn()

    render(
      <ProfileMenu
        profileMenuOpen={true}
        setProfileMenuOpen={setProfileMenuOpen}
        sidebarOpen={true}
        onNavigate={onNavigate}
        handleLogout={handleLogout}
        profileButtonRef={createRef<HTMLButtonElement>()}
      />,
    )

    await user.click(screen.getByRole("menuitem", { name: "Profile" }))
    await user.click(screen.getByRole("menuitem", { name: "Repositories" }))
    await user.click(screen.getByRole("menuitem", { name: "Diagnostics" }))
    await user.click(screen.getByRole("menuitem", { name: "Settings" }))
    await user.click(screen.getByRole("menuitem", { name: "Help" }))
    await user.click(screen.getByRole("menuitem", { name: "Log out" }))

    expect(onNavigate).toHaveBeenNthCalledWith(1, "/profile")
    expect(onNavigate).toHaveBeenNthCalledWith(2, "/repositories")
    expect(onNavigate).toHaveBeenNthCalledWith(3, "/diagnostics")
    expect(onNavigate).toHaveBeenNthCalledWith(4, "/settings")
    expect(onNavigate).toHaveBeenNthCalledWith(5, "/help")
    expect(handleLogout).toHaveBeenCalledOnce()
    expect(setProfileMenuOpen).toHaveBeenCalledWith(false)
  })
})
