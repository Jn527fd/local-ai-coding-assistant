import { useState } from "react";

const PROMPT_CARDS = [
  "Explain the auth flow",
  "Find where API requests are handled",
  "Generate tests for the selected file",
  "Summarize recent architectural risks",
];

function EmptyChatState({ hasIndexedRepository, onIndexRepository, onPrompt }) {
  return (
    <div className="chat-empty-state">
      <div className="chat-empty-state__badge">Local code intelligence</div>
      <h1>Ask your codebase anything</h1>
      <p>
        Private answers grounded in local files. Nothing leaves this machine.
      </p>

      <div className="prompt-grid" aria-label="Suggested prompts">
        {PROMPT_CARDS.map((prompt) => (
          <button
            className="prompt-card"
            key={prompt}
            onClick={() => onPrompt(prompt)}
            type="button"
          >
            <span>{prompt}</span>
            <small>Use as prompt</small>
          </button>
        ))}
      </div>

      {!hasIndexedRepository && (
        <button
          className="secondary-button empty-index-button"
          onClick={onIndexRepository}
          type="button"
        >
          Index a local repository
        </button>
      )}
    </div>
  );
}

function StreamingResponse() {
  return (
    <article className="chat-message chat-message--assistant">
      <span className="chat-message__role">Assistant</span>
      <div className="streaming-lines" aria-label="Assistant is responding">
        <span />
        <span />
        <span />
      </div>
    </article>
  );
}

function ChatBox({
  activeChat,
  activeModel,
  composerRef,
  error,
  hasIndexedRepository,
  indexedRepository,
  isSending,
  notice,
  onDeleteChat,
  onIndexRepository,
  onSendMessage,
}) {
  const [message, setMessage] = useState("");

  function applyPrompt(prompt) {
    setMessage(prompt);
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }

    const didSend = await onSendMessage(trimmed);
    if (didSend) {
      setMessage("");
    }
  }

  const messages = activeChat?.messages || [];
  const hasMessages = messages.length > 0;

  return (
    <section className="chat-workspace-panel" aria-label="Chat workspace">
      <div className="chat-thread-header">
        <div>
          <span className="header-kicker">Thread</span>
          <h2>{activeChat?.title || "Untitled thread"}</h2>
        </div>
        <div className="chat-thread-actions">
          <button
            className="ghost-button"
            disabled={!activeChat || isSending}
            onClick={onDeleteChat}
            type="button"
          >
            Delete thread
          </button>
        </div>
      </div>

      <div className="chat-scroll-region" aria-live="polite">
        {!hasMessages ? (
          <EmptyChatState
            hasIndexedRepository={hasIndexedRepository}
            onIndexRepository={onIndexRepository}
            onPrompt={applyPrompt}
          />
        ) : (
          <div className="message-stack">
            {messages.map((item, index) => (
              <article
                className={`chat-message chat-message--${item.role}`}
                key={`${activeChat.id}-${item.role}-${index}`}
              >
                <span className="chat-message__role">
                  {item.role === "user" ? "You" : "Assistant"}
                </span>
                <p>{item.content}</p>
              </article>
            ))}
            {isSending && <StreamingResponse />}
          </div>
        )}

        {!hasMessages && isSending && <StreamingResponse />}
      </div>

      {error && (
        <div className="composer-error" role="alert">
          {error}
        </div>
      )}
      {notice && <div className="composer-notice">{notice}</div>}

      <form className="chat-composer" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="chat-message">
          Ask about your codebase
        </label>
        <textarea
          disabled={!activeChat}
          id="chat-message"
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Ask about your codebase..."
          ref={composerRef}
          rows="3"
          value={message}
        />
        <div className="composer-toolbar">
          <div className="composer-actions">
            <button
              className="ghost-button"
              onClick={onIndexRepository}
              type="button"
            >
              Attach context
            </button>
            <button className="ghost-button" type="button">
              Scope: {indexedRepository?.name || "workspace"}
            </button>
          </div>
          <button
            className="primary-button send-button"
            disabled={!activeChat || isSending || !message.trim()}
            type="submit"
          >
            {isSending ? "Sending..." : "Send"}
          </button>
        </div>
        <div className="composer-metadata">
          <span>Model: {activeModel || "checking"}</span>
          <span>
            Context: {indexedRepository?.name || "no repository indexed"}
          </span>
          <span>Local only</span>
        </div>
      </form>
    </section>
  );
}

export default ChatBox;
