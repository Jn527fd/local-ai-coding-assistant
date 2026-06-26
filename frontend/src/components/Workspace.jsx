import { useEffect, useRef, useState } from "react";

import Conversation from "./Conversation.jsx";
import { Button } from "./ui.jsx";

function ThreadMenu({
  disabled,
  isOpen,
  onClose,
  onDelete,
  onExport,
  onRename,
  onToggle,
}) {
  const menuRef = useRef(null);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (!menuRef.current?.contains(event.target)) {
        onClose?.();
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [isOpen, onClose]);

  return (
    <div
      className="thread-menu"
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          onClose?.();
        }
      }}
      ref={menuRef}
    >
      <Button
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-label="Open thread actions"
        className="thread-menu__trigger"
        disabled={disabled}
        onClick={onToggle}
        type="button"
        variant="ghost"
      >
        ...
      </Button>
      {isOpen && (
        <div aria-label="Thread actions" className="thread-menu__content" role="menu">
          <Button className="thread-menu__item" onClick={onRename} role="menuitem" variant="ghost">
            Rename
          </Button>
          <Button className="thread-menu__item" onClick={onExport} role="menuitem" variant="ghost">
            Export
          </Button>
          <Button className="thread-menu__item thread-menu__item--danger" onClick={onDelete} role="menuitem" variant="ghost">
            Delete
          </Button>
        </div>
      )}
    </div>
  );
}

function Workspace({
  activeChat,
  error,
  isSending,
  onDeleteChat,
  onDeleteMessage,
  onExportChat,
  onOpenSourceDetails,
  onRenameChat,
}) {
  const [threadMenuOpen, setThreadMenuOpen] = useState(false);
  const hasMessages = Boolean(activeChat?.messages?.length);

  function runThreadAction(callback) {
    setThreadMenuOpen(false);
    callback?.();
  }

  return (
    <main className="workspace main-content" aria-label="Chat workspace">
      {hasMessages && (
        <div className="workspace-thread-bar">
          <div>
            <span className="header-kicker">Thread</span>
            <h2>{activeChat?.title || "Untitled thread"}</h2>
          </div>
          <div className="chat-thread-actions">
            <ThreadMenu
              disabled={!activeChat || isSending}
              isOpen={threadMenuOpen}
              onClose={() => setThreadMenuOpen(false)}
              onDelete={() => runThreadAction(onDeleteChat)}
              onExport={() => runThreadAction(onExportChat)}
              onRename={() => runThreadAction(onRenameChat)}
              onToggle={() => setThreadMenuOpen((current) => !current)}
            />
          </div>
        </div>
      )}

      <Conversation
        activeChat={activeChat}
        isSending={isSending}
        onDeleteMessage={onDeleteMessage}
        onOpenSourceDetails={onOpenSourceDetails}
      />

      <div className="workspace-feedback">
        {error && (
          <div className="composer-error" role="alert">
            {error}
          </div>
        )}
      </div>
    </main>
  );
}

export default Workspace;
