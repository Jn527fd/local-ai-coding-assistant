import { useEffect, useMemo, useRef, useState } from "react";

import { CommandItem, Input } from "./ui.jsx";

const COMMANDS = [
  {
    id: "new-chat",
    title: "New chat",
    description: "Create a fresh local thread.",
    shortcut: "Ctrl N",
  },
  {
    id: "focus-composer",
    title: "Focus composer",
    description: "Jump back to the main prompt input.",
    shortcut: "Ctrl L",
  },
  {
    id: "settings",
    title: "Open settings",
    description: "Manage account, API access, and local model settings.",
    shortcut: "S",
  },
  {
    id: "toggle-sidebar",
    title: "Toggle recents",
    description: "Open or close the recent conversations drawer.",
    shortcut: "B",
  },
  {
    id: "clear-thread",
    title: "Clear thread",
    description: "Delete the current chat from this browser.",
    shortcut: "Del",
  },
];

function CommandPalette({ isOpen, onClose, onRunCommand }) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const paletteRef = useRef(null);

  const filteredCommands = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return COMMANDS;
    }

    return COMMANDS.filter((command) =>
      `${command.title} ${command.description}`.toLowerCase().includes(normalized),
    );
  }, [query]);

  useEffect(() => {
    if (isOpen) {
      setSelectedIndex(0);
      setQuery("");
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  if (!isOpen) {
    return null;
  }

  function runSelectedCommand(index = selectedIndex) {
    const command = filteredCommands[index];
    if (!command) {
      return;
    }
    onRunCommand(command.id);
    onClose();
  }

  function handleKeyDown(event) {
    if (event.key === "Escape") {
      event.preventDefault();
      onClose();
      return;
    }

    if (event.key === "ArrowDown") {
      event.preventDefault();
      setSelectedIndex((current) =>
        filteredCommands.length ? (current + 1) % filteredCommands.length : 0,
      );
      return;
    }

    if (event.key === "ArrowUp") {
      event.preventDefault();
      setSelectedIndex((current) =>
        filteredCommands.length
          ? (current - 1 + filteredCommands.length) % filteredCommands.length
          : 0,
      );
      return;
    }

    if (event.key === "Home") {
      event.preventDefault();
      setSelectedIndex(0);
      return;
    }

    if (event.key === "End") {
      event.preventDefault();
      setSelectedIndex(Math.max(filteredCommands.length - 1, 0));
      return;
    }

    if (event.key === "Enter") {
      event.preventDefault();
      runSelectedCommand();
      return;
    }

    if (event.key !== "Tab") {
      return;
    }

    const focusableElements = Array.from(
      paletteRef.current?.querySelectorAll(
        'button, input, [href], select, textarea, [tabindex]:not([tabindex="-1"])',
      ) || [],
    ).filter((element) => !element.disabled);

    if (focusableElements.length === 0) {
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  }

  return (
    <div className="command-overlay" role="presentation" onMouseDown={onClose}>
      <section
        aria-label="Command palette"
        aria-modal="true"
        className="command-palette"
        onKeyDown={handleKeyDown}
        onMouseDown={(event) => event.stopPropagation()}
        ref={paletteRef}
        role="dialog"
      >
        <label className="command-search">
          <span className="sr-only">Command palette</span>
          <Input
            aria-activedescendant={
              filteredCommands[selectedIndex]
                ? `command-${filteredCommands[selectedIndex].id}`
                : undefined
            }
            aria-controls="command-list"
            autoFocus
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search, ask, or run a command..."
            value={query}
          />
        </label>

        <div className="command-list" id="command-list" role="list">
          {filteredCommands.map((command, index) => (
            <CommandItem
              aria-current={selectedIndex === index ? "true" : undefined}
              className={`command-item ${selectedIndex === index ? "command-item--active" : ""}`}
              id={`command-${command.id}`}
              key={command.id}
              onClick={() => {
                runSelectedCommand(index);
              }}
              onMouseEnter={() => setSelectedIndex(index)}
              shortcut={command.shortcut}
            >
              <strong>{command.title}</strong>
            </CommandItem>
          ))}
          {filteredCommands.length === 0 && (
            <p className="command-empty">No matching local commands.</p>
          )}
        </div>
      </section>
    </div>
  );
}

export default CommandPalette;
