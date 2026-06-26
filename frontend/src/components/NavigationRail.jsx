import { useEffect, useMemo, useState } from "react";

import { formatRelativeTime, MAX_CHATS } from "../chatState.js";
import { Button, IconButton, Input } from "./ui.jsx";

function Icon({ name }) {
  const common = {
    "aria-hidden": "true",
    className: "nav-icon",
    fill: "none",
    viewBox: "0 0 24 24",
    xmlns: "http://www.w3.org/2000/svg",
  };

  const paths = {
    app: "M12 3.5 19.5 8v8L12 20.5 4.5 16V8L12 3.5Zm-4.5 6.1L12 12.2l4.5-2.6M12 12.2v5.1",
    ask: "M5 6.75A3.75 3.75 0 0 1 8.75 3h6.5A3.75 3.75 0 0 1 19 6.75v4.5A3.75 3.75 0 0 1 15.25 15H12l-4.5 4v-4A3.75 3.75 0 0 1 4 11.25v-4.5Z",
    menu: "M4.75 7.25h14.5M4.75 12h14.5M4.75 16.75h14.5",
    search: "m20 20-4.35-4.35M18 10.5a7.5 7.5 0 1 1-15 0 7.5 7.5 0 0 1 15 0Z",
    plus: "M12 5v14M5 12h14",
    pencil: "M4.75 16.75 4 20l3.25-.75L18.5 8 16 5.5 4.75 16.75Z M14.75 6.75l2.5 2.5",
    settings: "M12 8.25A3.75 3.75 0 1 1 12 15.75 3.75 3.75 0 0 1 12 8.25Zm7.1 3.75c0-.5-.05-.98-.16-1.44l2-1.56-2-3.46-2.42.98a7.7 7.7 0 0 0-2.48-1.43L13.68 2h-4l-.36 3.09a7.7 7.7 0 0 0-2.48 1.43l-2.42-.98-2 3.46 2 1.56A7.3 7.3 0 0 0 4.26 12c0 .5.05.98.16 1.44l-2 1.56 2 3.46 2.42-.98a7.7 7.7 0 0 0 2.48 1.43l.36 3.09h4l.36-3.09a7.7 7.7 0 0 0 2.48-1.43l2.42.98 2-3.46-2-1.56c.1-.46.16-.94.16-1.44Z",
    trash: "M6 7.5h12M9 7.5V5.25h6V7.5m-7.5 0 .75 12h7.5l.75-12M10.5 10.5v6M13.5 10.5v6",
    x: "M6 6l12 12M18 6 6 18",
  };

  return (
    <svg {...common}>
      <path d={paths[name] || paths.ask} stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" />
    </svg>
  );
}

function RailIconButton({ active = false, children, className = "", label, ...props }) {
  return (
    <IconButton
      className={`rail-icon-button ${active ? "rail-icon-button--active" : ""} ${className}`}
      label={label}
      title={label}
      {...props}
    >
      {children}
    </IconButton>
  );
}

function groupChatsByTime(chats) {
  const groups = [
    { id: "previous-7", label: "Previous 7 Days", chats: [] },
    { id: "previous-30", label: "Previous 30 Days", chats: [] },
    { id: "older", label: "Older", chats: [] },
  ];
  const now = Date.now();

  chats.forEach((chat) => {
    const updatedAt = new Date(chat.updatedAt).getTime();
    const ageInDays = Number.isFinite(updatedAt)
      ? (now - updatedAt) / (1000 * 60 * 60 * 24)
      : 31;

    if (ageInDays <= 7) {
      groups[0].chats.push(chat);
    } else if (ageInDays <= 30) {
      groups[1].chats.push(chat);
    } else {
      groups[2].chats.push(chat);
    }
  });

  return groups.filter((group) => group.chats.length > 0);
}

function RecentsDrawer({
  activeChatId,
  chats,
  isOpen,
  onClose,
  onDeleteChat,
  onNewChat,
  onRenameChat,
  onSelectChat,
}) {
  const [query, setQuery] = useState("");

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const filteredChats = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    const sortedChats = [...chats].sort(
      (left, right) => new Date(right.updatedAt).getTime() - new Date(left.updatedAt).getTime(),
    );

    if (!normalizedQuery) {
      return sortedChats;
    }

    return sortedChats.filter((chat) => chat.title.toLowerCase().includes(normalizedQuery));
  }, [chats, query]);

  const groupedChats = useMemo(() => groupChatsByTime(filteredChats), [filteredChats]);

  if (!isOpen) {
    return null;
  }

  function handleNewChat() {
    onNewChat();
    onClose();
  }

  function handleSelectChat(chatId) {
    onSelectChat(chatId);
    onClose();
  }

  return (
    <aside
      aria-label="Recent conversations drawer"
      className="recents-drawer"
    >
      <div className="recents-drawer__search-row">
        <label className="sr-only" htmlFor="recent-chat-search">
          Search chats
        </label>
        <Input
          autoFocus
          className="recents-drawer__search"
          id="recent-chat-search"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search chats..."
          type="search"
          value={query}
        />
        <IconButton className="recents-drawer__close" label="Close recents" onClick={onClose}>
          <Icon name="x" />
        </IconButton>
      </div>

      <div className="recents-drawer__body">
        <Button className="recents-drawer__new-chat" onClick={handleNewChat} type="button" variant="ghost">
          <Icon name="pencil" />
          <span>New chat</span>
        </Button>

        {groupedChats.length > 0 ? (
          groupedChats.map((group) => (
            <section className="recents-group" key={group.id} aria-label={group.label}>
              <h2>{group.label}</h2>
              <div className="recents-list">
                {group.chats.map((chat) => (
                  <article
                    className={`recents-row ${chat.id === activeChatId ? "recents-row--active" : ""}`}
                    key={chat.id}
                  >
                    <button
                      className="recents-row__main"
                      onClick={() => handleSelectChat(chat.id)}
                      type="button"
                    >
                      <Icon name="ask" />
                      <span>
                        <strong>{chat.title}</strong>
                        <small>{formatRelativeTime(chat.updatedAt)}</small>
                      </span>
                    </button>
                    <div className="recents-row__actions" aria-label={`Actions for ${chat.title}`}>
                      <IconButton label={`Rename ${chat.title}`} onClick={() => onRenameChat(chat.id)}>
                        <Icon name="pencil" />
                      </IconButton>
                      <IconButton label={`Delete ${chat.title}`} onClick={() => onDeleteChat(chat.id)}>
                        <Icon name="trash" />
                      </IconButton>
                    </div>
                  </article>
                ))}
              </div>
            </section>
          ))
        ) : (
          <p className="recents-drawer__empty">
            {query ? "No matching chats." : "No recent conversations yet."}
          </p>
        )}
      </div>
    </aside>
  );
}

function NavigationRail({
  activeChatId,
  chats,
  currentSection,
  drawerOpen,
  onCloseDrawer,
  onDeleteChat = () => {},
  onNewChat,
  onOpenSettings,
  onRenameChat = () => {},
  onSelectChat,
  onSelectSection,
  onToggleDrawer,
}) {
  function openSettings() {
    onOpenSettings();
    onSelectSection("settings");
    onCloseDrawer();
  }

  function startNewChat() {
    onNewChat();
    onCloseDrawer();
  }

  return (
    <>
      <aside aria-label="Primary navigation" className="navigation-rail navigation-rail--icon-only">
        <div className="navigation-rail__inner">
          <div className="rail-icon-stack rail-icon-stack--top">
            <RailIconButton active={drawerOpen} label="Menu and recents" onClick={onToggleDrawer}>
              <Icon name="menu" />
            </RailIconButton>
            <RailIconButton label={`New chat. ${chats.length} of ${MAX_CHATS} used`} onClick={startNewChat}>
              <Icon name="plus" />
            </RailIconButton>
          </div>

          <div className="navigation-rail__spacer" />

          <div className="rail-icon-stack rail-icon-stack--bottom">
            <RailIconButton active={currentSection === "settings"} label="Settings" onClick={openSettings}>
              <Icon name="settings" />
            </RailIconButton>
          </div>
        </div>
      </aside>

      <RecentsDrawer
        activeChatId={activeChatId}
        chats={chats}
        isOpen={drawerOpen}
        onClose={onCloseDrawer}
        onDeleteChat={onDeleteChat}
        onNewChat={onNewChat}
        onRenameChat={onRenameChat}
        onSelectChat={onSelectChat}
      />
    </>
  );
}

export default NavigationRail;
