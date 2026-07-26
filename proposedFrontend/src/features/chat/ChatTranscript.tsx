import { useEffect, useMemo, useState } from "react"
import type { ChatMessage, Conversation } from "../conversations/types"

const MESSAGE_WINDOW = 100

export function ChatTranscript({
  activeConversation,
  tempChat,
  showMessageTimestamps = true,
  onCancelMessage,
  onRetryMessage,
  onRegenerateMessage,
}: {
  activeConversation?: Conversation
  tempChat: boolean
  showMessageTimestamps?: boolean
  onCancelMessage: (messageId: string) => void
  onRetryMessage: (messageId: string) => void
  onRegenerateMessage: (messageId: string) => void
}) {
  const conversationId = activeConversation?.id ?? null
  const [messageWindow, setMessageWindow] = useState({
    conversationId,
    count: MESSAGE_WINDOW,
  })
  const [nearBottom, setNearBottom] = useState(true)
  const messages = useMemo(
    () => activeConversation?.messages ?? [],
    [activeConversation?.messages],
  )
  const visibleCount =
    messageWindow.conversationId === conversationId
      ? messageWindow.count
      : MESSAGE_WINDOW
  const visibleMessages = useMemo(
    () => messages.slice(Math.max(0, messages.length - visibleCount)),
    [messages, visibleCount],
  )

  useEffect(() => {
    const updateNearBottom = () => {
      const distance =
        document.documentElement.scrollHeight -
        (window.scrollY + window.innerHeight)
      setNearBottom(distance < 160)
    }
    updateNearBottom()
    window.addEventListener("scroll", updateNearBottom, { passive: true })
    return () => window.removeEventListener("scroll", updateNearBottom)
  }, [])

  useEffect(() => {
    if (!nearBottom) return
    window.requestAnimationFrame(() => {
      window.scrollTo({ top: document.documentElement.scrollHeight })
    })
  }, [messages, nearBottom])

  const hasMessages = messages.length > 0
  const latestAssistant = [...messages]
    .reverse()
    .find((message) => message.role === "assistant")
  const assistantAnnouncement = latestAssistant
    ? latestAssistant.status === "complete"
      ? `New assistant message: ${latestAssistant.content}`
      : latestAssistant.status === "failed"
        ? `Assistant response failed: ${latestAssistant.error ?? "Response failed"}`
        : latestAssistant.status === "stopped"
          ? "Assistant response stopped"
          : latestAssistant.status === "streaming"
            ? "Assistant is responding"
            : "Waiting for assistant response"
    : ""

  return (
    <main
      id="main-content"
      className="chat-main"
      tabIndex={-1}
      style={{
        position: "relative",
        marginLeft: 56,
        marginRight: 52,
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: hasMessages ? "flex-start" : "center",
        paddingTop: hasMessages ? 78 : 0,
        paddingBottom: 150,
      }}
    >
      {tempChat && (
        <div className="temporary-chat-banner">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 2a10 10 0 1 1 0 20A10 10 0 0 1 12 2z"
              stroke="currentColor"
              strokeWidth="2"
            />
            <path
              d="M12 6v6l4 2"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
          Temporary chat — excluded from saved conversation history
        </div>
      )}

      {hasMessages ? (
        <div
          className="chat-thread"
          role="log"
          aria-label="Conversation messages"
          aria-relevant="additions text"
        >
          <div className="sr-only" aria-live="polite" aria-atomic="true">
            {assistantAnnouncement}
          </div>
          <div className="chat-thread-heading">
            <span>Conversation</span>
            <h1>{activeConversation?.title}</h1>
          </div>
          {messages.length > visibleMessages.length && (
            <button
              type="button"
              className="load-earlier-messages"
              onClick={() =>
                setMessageWindow({
                  conversationId,
                  count: visibleCount + MESSAGE_WINDOW,
                })
              }
            >
              Show earlier messages
            </button>
          )}
          {visibleMessages.map((message) => (
            <MessageRow
              key={message.id}
              message={message}
              showMessageTimestamps={showMessageTimestamps}
              onCancel={() => onCancelMessage(message.id)}
              onRetry={() => onRetryMessage(message.id)}
              onRegenerate={() => onRegenerateMessage(message.id)}
            />
          ))}
        </div>
      ) : (
        <EmptyChatState />
      )}
    </main>
  )
}

function MessageRow({
  message,
  showMessageTimestamps,
  onCancel,
  onRetry,
  onRegenerate,
}: {
  message: ChatMessage
  showMessageTimestamps: boolean
  onCancel: () => void
  onRetry: () => void
  onRegenerate: () => void
}) {
  const isAssistant = message.role === "assistant"
  return (
    <article
      className={`chat-message-row ${message.role}`}
      aria-label={`${message.role === "user" ? "Your" : "Assistant"} message`}
    >
      <div className="chat-message-avatar" aria-hidden="true">
        {message.role === "user" ? "T" : "L"}
      </div>
      <div className="chat-message-content">
        <span>{message.role === "user" ? "You" : "LocalChat"}</span>
        {showMessageTimestamps && (
          <time className="message-timestamp" dateTime={message.createdAt}>
            {new Date(message.createdAt).toLocaleTimeString([], {
              hour: "numeric",
              minute: "2-digit",
            })}
          </time>
        )}
        <SafeMarkdown content={message.content} />
        {message.attachments.length > 0 && (
          <div className="message-attachments">
            {message.attachments.map((attachment) => (
              <a
                key={attachment.id}
                href={attachment.url}
                target="_blank"
                rel="noreferrer"
              >
                {attachment.mediaType.startsWith("image/") && attachment.url ? (
                  <img
                    src={attachment.url}
                    alt={`Preview of ${attachment.filename}`}
                  />
                ) : (
                  <span aria-hidden="true">📎</span>
                )}
                {attachment.filename}
              </a>
            ))}
          </div>
        )}
        {message.status !== "complete" && (
          <div
            className={`message-status message-status-${message.status}`}
            role="status"
            aria-live={message.status === "failed" ? "assertive" : "polite"}
          >
            {message.status === "pending" && "Waiting for response…"}
            {message.status === "streaming" && "Responding…"}
            {message.status === "stopped" && "Response stopped"}
            {message.status === "failed" &&
              (message.error || "Response failed")}
          </div>
        )}
        <div className="message-actions">
          <button
            type="button"
            onClick={() => void navigator.clipboard.writeText(message.content)}
            disabled={!message.content}
            aria-label={`Copy ${isAssistant ? "assistant" : "your"} message`}
          >
            Copy
          </button>
          {isAssistant &&
            (message.status === "pending" ||
              message.status === "streaming") && (
              <button type="button" onClick={onCancel}>
                Stop
              </button>
            )}
          {isAssistant &&
            (message.status === "failed" || message.status === "stopped") && (
              <button type="button" onClick={onRetry}>
                Retry
              </button>
            )}
          {isAssistant && message.status === "complete" && (
            <button type="button" onClick={onRegenerate}>
              Regenerate
            </button>
          )}
        </div>
      </div>
    </article>
  )
}

function SafeMarkdown({ content }: { content: string }) {
  const sections = content.split("```")
  return (
    <div className="safe-markdown">
      {sections.map((section, index) => {
        if (index % 2 === 1) {
          const [firstLine = "", ...codeLines] = section.split("\n")
          const language = /^[\w+-]+$/.test(firstLine.trim())
            ? firstLine.trim()
            : "text"
          const code = language === "text" ? section : codeLines.join("\n")
          return (
            <div className="code-block" key={`${index}-${code.slice(0, 20)}`}>
              <div>
                <span>{language}</span>
                <button
                  type="button"
                  onClick={() => void navigator.clipboard.writeText(code)}
                >
                  Copy code
                </button>
              </div>
              <pre>
                <code className={`language-${language}`}>{code}</code>
              </pre>
            </div>
          )
        }
        return section
          .split(/\n{2,}/)
          .filter(Boolean)
          .map((paragraph, paragraphIndex) => (
            <p key={`${index}-${paragraphIndex}`}>{paragraph}</p>
          ))
      })}
    </div>
  )
}

function EmptyChatState() {
  return (
    <>
      <div className="empty-chat-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
          <path
            d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
            fill="white"
          />
        </svg>
      </div>
      <h1 className="empty-chat-heading">What can I help with?</h1>
      <p className="empty-chat-copy">Ask anything, upload files or images.</p>
    </>
  )
}
