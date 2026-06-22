import { formatRelativeTime, MAX_CHATS } from "../chatState.js";

const NAV_ITEMS = [
  { id: "chat", label: "Chat", icon: "C" },
  { id: "codebase", label: "Codebase", icon: "{}" },
  { id: "search", label: "Search", icon: "/" },
  { id: "models", label: "Models", icon: "M" },
  { id: "settings", label: "Settings", icon: "S" },
];

function WorkspaceSidebar({
  activeChatId,
  activeModel,
  chats,
  collapsed,
  currentSection,
  isOllamaOnline,
  onNewChat,
  onOpenSettings,
  onSelectChat,
  onSelectSection,
  onToggleCollapsed,
}) {
  return (
    <aside
      aria-label="Workspace navigation"
      className={`workspace-sidebar ${collapsed ? "workspace-sidebar--collapsed" : ""}`}
    >
      <div className="workspace-switcher">
        <button
          aria-label="Switch workspace"
          className="workspace-switcher__button"
          type="button"
        >
          <span className="workspace-switcher__mark">LA</span>
          <span className="workspace-sidebar__label">
            <strong>Local AI</strong>
            <small>Private workspace</small>
          </span>
        </button>
        <button
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="sidebar-toggle"
          onClick={onToggleCollapsed}
          type="button"
        >
          {collapsed ? ">" : "<"}
        </button>
      </div>

      <button className="new-chat-button" onClick={onNewChat} type="button">
        <span>+</span>
        <span className="workspace-sidebar__label">New chat</span>
      </button>

      <nav className="sidebar-nav" aria-label="Primary">
        {NAV_ITEMS.map((item) => (
          <button
            aria-current={currentSection === item.id ? "page" : undefined}
            className={`sidebar-nav__item ${
              currentSection === item.id ? "sidebar-nav__item--active" : ""
            }`}
            key={item.id}
            onClick={() => {
              if (item.id === "settings" || item.id === "models") {
                onOpenSettings();
              }
              onSelectSection(item.id);
            }}
            type="button"
          >
            <span className="sidebar-nav__icon">{item.icon}</span>
            <span className="workspace-sidebar__label">{item.label}</span>
          </button>
        ))}
      </nav>

      <section className="recent-chats" aria-label="Recent chats">
        <div className="sidebar-section-heading">
          <span className="workspace-sidebar__label">Recent chats</span>
          <span className="workspace-sidebar__label">
            {chats.length}/{MAX_CHATS}
          </span>
        </div>

        <div className="recent-chats__list">
          {chats.length === 0
            ? Array.from({ length: 3 }).map((_, index) => (
                <div className="recent-chat-skeleton" key={index}>
                  <span />
                  <span />
                </div>
              ))
            : chats.map((chat) => (
                <button
                  className={`recent-chat ${
                    chat.id === activeChatId ? "recent-chat--active" : ""
                  }`}
                  key={chat.id}
                  onClick={() => onSelectChat(chat.id)}
                  type="button"
                >
                  <span className="recent-chat__title">{chat.title}</span>
                  <span className="recent-chat__meta">
                    {chat.messages.length} messages -{" "}
                    {formatRelativeTime(chat.updatedAt)}
                  </span>
                </button>
              ))}
        </div>
      </section>

      <div className="sidebar-status-pill" aria-live="polite">
        <span
          className={`status-dot ${isOllamaOnline ? "status-dot--online" : "status-dot--offline"}`}
        />
        <span className="workspace-sidebar__label">
          <strong>{isOllamaOnline ? "Ollama online" : "Ollama offline"}</strong>
          <small>{activeModel || "No active model"}</small>
        </span>
      </div>
    </aside>
  );
}

export default WorkspaceSidebar;
