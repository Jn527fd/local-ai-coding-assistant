import { useEffect, useMemo, useState } from "react";

import { sendChat } from "../api.js";

const MAX_CHATS = 5;
const STORAGE_PREFIX = "local-ai-coding-assistant.chats";

function createChat() {
  return {
    id:
      typeof globalThis.crypto?.randomUUID === "function"
        ? globalThis.crypto.randomUUID()
        : `${Date.now()}-${Math.random()}`,
    title: "New chat",
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}

function loadChats(username) {
  const storageKey = `${STORAGE_PREFIX}.${username}`;
  try {
    const parsed = JSON.parse(window.localStorage.getItem(storageKey) || "[]");
    if (!Array.isArray(parsed)) {
      return [createChat()];
    }

    const validChats = parsed
      .filter(
        (chat) =>
          chat &&
          typeof chat.id === "string" &&
          typeof chat.title === "string" &&
          Array.isArray(chat.messages),
      )
      .map((chat) => ({
        ...chat,
        messages: chat.messages.filter(
          (message) =>
            message &&
            (message.role === "user" || message.role === "assistant") &&
            typeof message.content === "string" &&
            message.content.length > 0,
        ),
      }))
      .slice(0, MAX_CHATS);
    return validChats.length > 0 ? validChats : [createChat()];
  } catch {
    return [createChat()];
  }
}

function titleFromMessage(message) {
  const singleLine = message.replace(/\s+/g, " ").trim();
  return singleLine.length > 38
    ? `${singleLine.slice(0, 38)}...`
    : singleLine;
}

function ChatBox({ activeModel, apiKey, username }) {
  const storageKey = `${STORAGE_PREFIX}.${username}`;
  const initialChats = useMemo(() => loadChats(username), [username]);
  const [chats, setChats] = useState(initialChats);
  const [activeChatId, setActiveChatId] = useState(
    initialChats[0]?.id || "",
  );
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [sendingChatId, setSendingChatId] = useState("");

  const activeChat = useMemo(
    () => chats.find((chat) => chat.id === activeChatId) || null,
    [activeChatId, chats],
  );

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(chats));
  }, [chats, storageKey]);

  function handleNewChat() {
    if (chats.length >= MAX_CHATS) {
      setError(
        "You already have five chats. Delete one before creating another.",
      );
      return;
    }

    const nextChat = createChat();
    setChats((current) => [nextChat, ...current]);
    setActiveChatId(nextChat.id);
    setMessage("");
    setError("");
  }

  function handleDeleteChat(chat) {
    const confirmed = window.confirm(
      `Delete "${chat.title}"? Its messages and model context will be erased from this browser.`,
    );
    if (!confirmed) {
      return;
    }

    setChats((current) => {
      const remaining = current.filter((item) => item.id !== chat.id);
      if (chat.id === activeChatId) {
        setActiveChatId(remaining[0]?.id || "");
      }
      return remaining;
    });
    setMessage("");
    setError("");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmedMessage = message.trim();

    if (!apiKey) {
      setError("Save and verify your API key from Account before chatting.");
      return;
    }

    if (!activeChat) {
      setError("Create a chat before sending a message.");
      return;
    }

    if (!trimmedMessage) {
      setError("Enter a message for the model.");
      return;
    }

    const chatId = activeChat.id;
    const history = activeChat.messages
      .slice(-30)
      .map(({ role, content }) => ({ role, content }));
    const userMessage = { role: "user", content: trimmedMessage };

    setError("");
    setMessage("");
    setSendingChatId(chatId);
    setChats((current) =>
      current.map((chat) =>
        chat.id === chatId
          ? {
              ...chat,
              title:
                chat.messages.length === 0
                  ? titleFromMessage(trimmedMessage)
                  : chat.title,
              messages: [...chat.messages, userMessage],
              updatedAt: new Date().toISOString(),
            }
          : chat,
      ),
    );

    try {
      const result = await sendChat(apiKey, trimmedMessage, history);
      setChats((current) =>
        current.map((chat) =>
          chat.id === chatId
            ? {
                ...chat,
                messages: [
                  ...chat.messages,
                  { role: "assistant", content: result.answer },
                ],
                updatedAt: new Date().toISOString(),
              }
            : chat,
        ),
      );
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSendingChatId("");
    }
  }

  return (
    <section className="panel panel--large">
      <div className="panel__heading">
        <div>
          <p className="section-kicker">Ollama</p>
          <h2>Chat with a local model</h2>
        </div>
        <span className="panel__tag">
          {activeModel || "Checking model..."}
        </span>
      </div>

      <div className="chat-workspace">
        <aside className="chat-list" aria-label="Saved chats">
          <div className="chat-list__header">
            <div>
              <strong>Chats</strong>
              <span>
                {chats.length}/{MAX_CHATS}
              </span>
            </div>
            <button
              className="chat-new-button"
              disabled={chats.length >= MAX_CHATS}
              onClick={handleNewChat}
              type="button"
            >
              New
            </button>
          </div>

          <div className="chat-list__items">
            {chats.map((chat) => (
              <div
                className={`chat-list__item ${
                  chat.id === activeChatId ? "chat-list__item--active" : ""
                }`}
                key={chat.id}
              >
                <button
                  className="chat-select-button"
                  onClick={() => {
                    setActiveChatId(chat.id);
                    setError("");
                  }}
                  type="button"
                >
                  <span>{chat.title}</span>
                  <small>{chat.messages.length} messages</small>
                </button>
                <button
                  aria-label={`Delete ${chat.title}`}
                  className="chat-delete-button"
                  disabled={sendingChatId === chat.id}
                  onClick={() => handleDeleteChat(chat)}
                  type="button"
                >
                  Delete
                </button>
              </div>
            ))}
          </div>

          {chats.length === 0 && (
            <div className="chat-list__empty">
              <p>No saved chats.</p>
              <button
                className="secondary-button"
                onClick={handleNewChat}
                type="button"
              >
                Create chat
              </button>
            </div>
          )}
        </aside>

        <div className="chat-main">
          <div className="conversation" aria-live="polite">
            {!activeChat || activeChat.messages.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state__mark">&gt;_</div>
                <h3>Start a local coding conversation</h3>
                <p>
                  Each chat has separate context. Delete a chat to erase its
                  stored messages and prevent them from being sent again.
                </p>
              </div>
            ) : (
              activeChat.messages.map((item, index) => (
                <article
                  className={`message message--${item.role}`}
                  key={`${activeChat.id}-${item.role}-${index}`}
                >
                  <span>{item.role === "user" ? "You" : "Assistant"}</span>
                  <p>{item.content}</p>
                </article>
              ))
            )}

            {sendingChatId === activeChatId && (
              <article className="message message--assistant message--loading">
                <span>Assistant</span>
                <p>Thinking locally...</p>
              </article>
            )}
          </div>

          {error && <div className="alert alert--error">{error}</div>}

          <form className="stacked-form" onSubmit={handleSubmit}>
            <label className="field">
              <span className="field__label">Message</span>
              <textarea
                disabled={!activeChat}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Explain how dependency injection works in FastAPI..."
                rows="4"
                value={message}
              />
            </label>

            <div className="form-actions">
              <span className="form-hint">
                Context follows this chat when models change. Maximum five
                local chats.
              </span>
              <button
                className="primary-button"
                disabled={Boolean(sendingChatId) || !activeChat}
                type="submit"
              >
                {sendingChatId ? "Sending..." : "Send message"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}

export default ChatBox;
