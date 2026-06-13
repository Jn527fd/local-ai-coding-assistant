import { useState } from "react";

import { sendChat } from "../api.js";

function ChatBox({ apiKey }) {
  const [model, setModel] = useState("qwen3:4b");
  const [message, setMessage] = useState("");
  const [conversation, setConversation] = useState([]);
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmedMessage = message.trim();

    if (!apiKey) {
      setError("Enter your API key before sending a protected request.");
      return;
    }

    if (!trimmedMessage) {
      setError("Enter a message for the model.");
      return;
    }

    if (!model.trim()) {
      setError("Enter an Ollama model name.");
      return;
    }

    setError("");
    setMessage("");
    setConversation((current) => [
      ...current,
      { role: "user", content: trimmedMessage },
    ]);
    setIsSubmitting(true);

    try {
      const result = await sendChat(apiKey, model.trim(), trimmedMessage);
      setConversation((current) => [
        ...current,
        { role: "assistant", content: result.answer },
      ]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="panel panel--large">
      <div className="panel__heading">
        <div>
          <p className="section-kicker">Ollama</p>
          <h2>Chat with a local model</h2>
        </div>
        <span className="panel__tag">Private inference</span>
      </div>

      <div className="conversation" aria-live="polite">
        {conversation.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state__mark">&gt;_</div>
            <h3>Start a local coding conversation</h3>
            <p>
              Ask for an explanation, a refactor idea, or help understanding an
              error. Requests go directly to your Ollama server.
            </p>
          </div>
        ) : (
          conversation.map((item, index) => (
            <article
              className={`message message--${item.role}`}
              key={`${item.role}-${index}`}
            >
              <span>{item.role === "user" ? "You" : "Assistant"}</span>
              <p>{item.content}</p>
            </article>
          ))
        )}

        {isSubmitting && (
          <article className="message message--assistant message--loading">
            <span>Assistant</span>
            <p>Thinking locally...</p>
          </article>
        )}
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <form className="stacked-form" onSubmit={handleSubmit}>
        <label className="field field--compact">
          <span className="field__label">Model</span>
          <input
            onChange={(event) => setModel(event.target.value)}
            required
            value={model}
          />
        </label>

        <label className="field">
          <span className="field__label">Message</span>
          <textarea
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Explain how dependency injection works in FastAPI..."
            rows="4"
            value={message}
          />
        </label>

        <div className="form-actions">
          <span className="form-hint">Uses the selected local Ollama model</span>
          <button
            className="primary-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Sending..." : "Send message"}
          </button>
        </div>
      </form>
    </section>
  );
}

export default ChatBox;
