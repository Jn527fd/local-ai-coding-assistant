import { useMemo, useState } from "react";

import { Button, Textarea } from "./ui.jsx";

const SLASH_COMMANDS = [
  {
    command: "/tests",
    description: "Review test coverage",
    prompt: "/tests Review coverage for the selected flow",
  },
  {
    command: "/explain",
    description: "Explain code, architecture, or behavior",
    prompt: "/explain How does this module work?",
  },
  {
    command: "/terminal",
    description: "Plan terminal commands safely",
    prompt: "/terminal What command should I run to verify this?",
  },
];

function PlusIcon() {
  return (
    <svg aria-hidden="true" className="composer-plus-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M12 5v14M5 12h14"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

function Composer({
  activeChat,
  composerRef,
  isSending,
  message,
  onMessageChange,
  onSendMessage,
}) {
  const [focused, setFocused] = useState(false);
  const [slashOpen, setSlashOpen] = useState(false);
  const [slashIndex, setSlashIndex] = useState(0);

  const slashQuery = useMemo(() => {
    const match = message.match(/(^|\s)(\/[a-z]*)$/i);
    return match?.[2]?.toLowerCase() || "";
  }, [message]);

  const filteredSlashCommands = useMemo(() => {
    if (!slashQuery) {
      return SLASH_COMMANDS;
    }
    return SLASH_COMMANDS.filter((item) => item.command.startsWith(slashQuery));
  }, [slashQuery]);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }

    onMessageChange("");
    setSlashOpen(false);

    const didSend = await onSendMessage(trimmed);

    if (!didSend) {
      onMessageChange(trimmed);
    }

    // const didSend = await onSendMessage(trimmed);
    // if (didSend) {
    //   onMessageChange("");
    //   setSlashOpen(false);
    // }
  }

  function closeMenus() {
    setSlashOpen(false);
  }

  function applyPrompt(prompt) {
    onMessageChange(prompt);
    closeMenus();
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  function applySlashCommand(item) {
    const nextValue = message.replace(/(^|\s)\/[a-z]*$/i, `$1${item.prompt}`);
    applyPrompt(nextValue.trimStart());
  }

  function handleMessageChange(event) {
    const nextValue = event.target.value;
    onMessageChange(nextValue);
    const nextSlash = nextValue.match(/(^|\s)(\/[a-z]*)$/i);
    setSlashOpen(Boolean(nextSlash));
    setSlashIndex(0);
  }

  function handleComposerKeyDown(event) {
    if (event.key === "Escape") {
      if (slashOpen) {
        event.preventDefault();
        closeMenus();
      }
      return;
    }

    if (slashOpen && filteredSlashCommands.length > 0) {
      if (event.key === "ArrowDown") {
        event.preventDefault();
        setSlashIndex((current) => (current + 1) % filteredSlashCommands.length);
        return;
      }
      if (event.key === "ArrowUp") {
        event.preventDefault();
        setSlashIndex(
          (current) =>
            (current - 1 + filteredSlashCommands.length) % filteredSlashCommands.length,
        );
        return;
      }
      if (event.key === "Enter" && !event.shiftKey && !(event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        applySlashCommand(filteredSlashCommands[slashIndex]);
        return;
      }
    }

    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form
      className={`composer smart-composer ${focused ? "smart-composer--focused" : ""}`}
      onSubmit={handleSubmit}
    >
      <div className="smart-composer__input-shell">
        <label className="sr-only" htmlFor="chat-message">
          Message assistant
        </label>
        <button
          aria-label="Attach file"
          className="composer-attach-button"
          title="Attachment placeholder"
          type="button"
        >
          <PlusIcon />
        </button>
        <Textarea
          aria-controls={slashOpen ? "slash-command-menu" : undefined}
          disabled={!activeChat}
          id="chat-message"
          onBlur={() => setFocused(false)}
          onChange={handleMessageChange}
          onFocus={() => setFocused(true)}
          onKeyDown={handleComposerKeyDown}
          placeholder="Ask anything"
          ref={composerRef}
          rows="1"
          value={message}
        />

        <div className="composer-inline-controls" aria-label="Composer controls">
          <Button
            className="primary-button send-button"
            disabled={!activeChat || isSending || !message.trim()}
            type="submit"
            variant="primary"
          >
            {isSending ? "Sending..." : "Send"}
          </Button>
        </div>

        {slashOpen && (
          <div
            aria-label="Slash commands"
            className="composer-popover slash-command-menu"
            id="slash-command-menu"
            role="listbox"
          >
            <div className="composer-popover__header">Slash commands</div>
            {filteredSlashCommands.length > 0 ? (
              filteredSlashCommands.map((item, index) => (
                <Button
                  aria-selected={slashIndex === index}
                  className={`slash-command-item ${
                    slashIndex === index ? "slash-command-item--active" : ""
                  }`}
                  key={item.command}
                  onMouseEnter={() => setSlashIndex(index)}
                  onClick={() => applySlashCommand(item)}
                  role="option"
                  type="button"
                  variant="ghost"
                >
                  <code>{item.command}</code>
                  <span>{item.description}</span>
                </Button>
              ))
            ) : (
              <p className="composer-empty-menu">No matching command.</p>
            )}
          </div>
        )}
      </div>

    </form>
  );
}

export default Composer;
/* 
<div className="smart-composer__footer">
  <div className="composer-submit-group">
    <span className="composer-shortcut">Ctrl Enter</span>
  </div>
</div> */