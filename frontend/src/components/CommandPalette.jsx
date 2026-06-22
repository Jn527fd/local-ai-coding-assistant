const COMMANDS = [
  {
    id: "new-chat",
    title: "New chat",
    description: "Create a fresh local conversation.",
    shortcut: "⌘N",
  },
  {
    id: "focus-composer",
    title: "Focus composer",
    description: "Jump back to the message input.",
    shortcut: "⌘L",
  },
  {
    id: "toggle-sidebar",
    title: "Toggle sidebar",
    description: "Collapse or expand navigation.",
    shortcut: "S",
  },
  {
    id: "toggle-context",
    title: "Toggle context panel",
    description: "Show or hide workspace context.",
    shortcut: "P",
  },
  {
    id: "settings",
    title: "Open settings",
    description: "Manage API key and local models.",
    shortcut: "G",
  },
];

function CommandPalette({ isOpen, onClose, onRunCommand }) {
  if (!isOpen) {
    return null;
  }

  return (
    <div className="command-overlay" role="presentation" onMouseDown={onClose}>
      <section
        aria-label="Command palette"
        aria-modal="true"
        className="command-palette"
        onMouseDown={(event) => event.stopPropagation()}
        role="dialog"
      >
        <label className="command-search">
          <span>Command palette</span>
          <input autoFocus placeholder="Type a command or shortcut..." />
        </label>

        <div className="command-list">
          {COMMANDS.map((command) => (
            <button
              className="command-item"
              key={command.id}
              onClick={() => {
                onRunCommand(command.id);
                onClose();
              }}
              type="button"
            >
              <span>
                <strong>{command.title}</strong>
                <small>{command.description}</small>
              </span>
              <kbd>{command.shortcut}</kbd>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

export default CommandPalette;
