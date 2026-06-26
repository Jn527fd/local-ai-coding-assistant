import { useEffect, useRef, useState } from "react";

import { Button, FileReference, SourceChip, Tooltip } from "./ui.jsx";

function formatMessageTime(value) {
  if (!value) {
    return "Just now";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Recently";
  }

  return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
}

function normalizeSource(source) {
  if (typeof source === "string") {
    return {
      label: source.split(/[\\/]/).pop() || source,
      path: source,
      snippet: "Inspect the cited local source.",
    };
  }

  return {
    label: source?.label || source?.file || source?.path || "Source",
    path: source?.path || source?.file || source?.label || "Local source",
    snippet:
      source?.snippet ||
      source?.preview ||
      "Inspect the cited local source.",
  };
}

function parseContentBlocks(content) {
  const blocks = [];
  const fencePattern = /```([^\n`]*)\n([\s\S]*?)```/g;
  let cursor = 0;
  let match;

  while ((match = fencePattern.exec(content)) !== null) {
    if (match.index > cursor) {
      blocks.push({ type: "text", content: content.slice(cursor, match.index) });
    }

    const rawMeta = match[1].trim();
    const [language = "text", maybeFilename = ""] = rawMeta.split(/\s+/);
    const filenameMatch = rawMeta.match(/(?:file|filename)=([^\s]+)/);
    blocks.push({
      type: "code",
      language: language || "text",
      filename: filenameMatch?.[1] || maybeFilename,
      content: match[2].replace(/\n$/, ""),
    });
    cursor = fencePattern.lastIndex;
  }

  if (cursor < content.length) {
    blocks.push({ type: "text", content: content.slice(cursor) });
  }

  return blocks.length > 0 ? blocks : [{ type: "text", content }];
}

async function copyText(value) {
  try {
    await navigator.clipboard?.writeText(value);
  } catch {
    // Clipboard access can be unavailable in local test/browser contexts.
  }
}

function exportMarkdown(filename, content) {
  try {
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  } catch {
    copyText(content);
  }
}

function formatGenerationTime(value) {
  if (!value) {
    return "local run";
  }

  if (value < 1000) {
    return `${Math.round(value)} ms`;
  }

  return `${(value / 1000).toFixed(value < 10000 ? 1 : 0)} s`;
}

function estimateTokenCount(content) {
  const text = `${content || ""}`.trim();
  if (!text) {
    return 0;
  }

  return Math.max(1, Math.ceil(text.split(/\s+/).length * 1.25));
}

function isRecentAssistantMessage(message) {
  const createdAt = new Date(message.createdAt).getTime();
  if (!Number.isFinite(createdAt)) {
    return false;
  }

  return Date.now() - createdAt < 6500;
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") {
      return undefined;
    }

    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!query) {
      return undefined;
    }

    setPrefersReducedMotion(Boolean(query.matches));

    function handleChange(event) {
      setPrefersReducedMotion(event.matches);
    }

    query.addEventListener?.("change", handleChange);
    query.addListener?.(handleChange);
    return () => {
      query.removeEventListener?.("change", handleChange);
      query.removeListener?.(handleChange);
    };
  }, []);

  return prefersReducedMotion;
}

function useProgressiveText(content, enabled) {
  const prefersReducedMotion = usePrefersReducedMotion();
  const shouldStream = enabled && !prefersReducedMotion && content.length > 0;
  const [visibleContent, setVisibleContent] = useState(() =>
    shouldStream ? "" : content,
  );

  useEffect(() => {
    if (!shouldStream) {
      setVisibleContent(content);
      return undefined;
    }

    let cursor = 0;
    let timeoutId;
    const chunkSize = Math.max(3, Math.ceil(content.length / 36));

    setVisibleContent("");

    function revealNextChunk() {
      cursor = Math.min(content.length, cursor + chunkSize);
      setVisibleContent(content.slice(0, cursor));

      if (cursor < content.length) {
        timeoutId = window.setTimeout(revealNextChunk, cursor < 80 ? 22 : 14);
      }
    }

    timeoutId = window.setTimeout(revealNextChunk, 80);
    return () => window.clearTimeout(timeoutId);
  }, [content, shouldStream]);

  return {
    isStreaming: shouldStream && visibleContent.length < content.length,
    visibleContent,
  };
}

function safeHref(value) {
  const href = value.trim();
  if (/^(https?:|mailto:|#)/i.test(href)) {
    return href;
  }
  return "#";
}

function renderInlineMarkdown(text) {
  const nodes = [];
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g;
  let cursor = 0;
  let match;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > cursor) {
      nodes.push(text.slice(cursor, match.index));
    }

    const token = match[0];
    if (token.startsWith("`")) {
      nodes.push(<code key={`${match.index}-code`}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("**")) {
      nodes.push(<strong key={`${match.index}-strong`}>{token.slice(2, -2)}</strong>);
    } else {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        nodes.push(
          <a
            href={safeHref(linkMatch[2])}
            key={`${match.index}-link`}
            rel="noreferrer"
            target="_blank"
          >
            {linkMatch[1]}
          </a>,
        );
      }
    }

    cursor = pattern.lastIndex;
  }

  if (cursor < text.length) {
    nodes.push(text.slice(cursor));
  }

  return nodes.length > 0 ? nodes : text;
}

function isTableSeparator(line) {
  return /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);
}

function splitTableRow(line) {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function isBlockStart(line, nextLine = "") {
  return (
    /^#{1,4}\s+/.test(line) ||
    /^>\s?/.test(line) ||
    /^[-*]\s+/.test(line) ||
    /^\d+\.\s+/.test(line) ||
    (line.includes("|") && isTableSeparator(nextLine))
  );
}

function parseMarkdownBlocks(content) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    const heading = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      blocks.push({
        type: "heading",
        level: heading[1].length,
        content: heading[2],
      });
      index += 1;
      continue;
    }

    if (trimmed.startsWith(">")) {
      const quote = [];
      while (index < lines.length && lines[index].trim().startsWith(">")) {
        quote.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push({ type: "quote", content: quote.join(" ") });
      continue;
    }

    if (trimmed.includes("|") && isTableSeparator(lines[index + 1] || "")) {
      const rows = [splitTableRow(trimmed)];
      index += 2;
      while (index < lines.length && lines[index].trim().includes("|")) {
        rows.push(splitTableRow(lines[index]));
        index += 1;
      }
      blocks.push({ type: "table", rows });
      continue;
    }

    if (/^[-*]\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      const ordered = /^\d+\.\s+/.test(trimmed);
      const items = [];
      while (index < lines.length) {
        const item = lines[index].trim();
        const match = ordered ? item.match(/^\d+\.\s+(.+)$/) : item.match(/^[-*]\s+(.+)$/);
        if (!match) {
          break;
        }
        items.push(match[1]);
        index += 1;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    const paragraph = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !isBlockStart(lines[index].trim(), lines[index + 1] || "")
    ) {
      paragraph.push(lines[index].trim());
      index += 1;
    }

    blocks.push({ type: "paragraph", content: paragraph.join(" ") });
  }

  return blocks;
}

function EmptyChatLanding() {
  return (
    <div className="empty-chat-landing">
      <div className="empty-hero-copy">
        <h1>Where should we begin?</h1>
        <p>
          Ask your local model a coding question. Your conversation stays on
          this machine.
        </p>
      </div>
    </div>
  );
}

function CodeBlock({ block }) {
  const [copied, setCopied] = useState(false);
  const lines = block.content.split("\n");
  const showLineNumbers = lines.length > 1;
  const filename = block.filename || "Generated snippet";
  const language = block.language || "text";

  async function handleCopy() {
    await copyText(block.content);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  }

  return (
    <div className="code-block">
      <div className="code-block__header">
        <div>
          <FileReference className="code-block__filename">{filename}</FileReference>
          <span className="code-block__language">{language}</span>
        </div>
        <Button
          aria-label={`Copy code from ${filename}`}
          className="code-block__copy"
          onClick={handleCopy}
          type="button"
          variant="ghost"
        >
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <pre>
        <code>
          {lines.map((line, index) => (
            <span className="code-line" key={index}>
              {showLineNumbers && <span className="code-line__number">{index + 1}</span>}
              <span className="code-line__content">{line || " "}</span>
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}

function MarkdownContent({ content }) {
  return (
    <div className="markdown-content">
      {parseMarkdownBlocks(content).map((block, index) => {
        if (block.type === "heading") {
          const HeadingTag = `h${Math.min(block.level + 1, 4)}`;
          return (
            <HeadingTag key={`${index}-heading`}>
              {renderInlineMarkdown(block.content)}
            </HeadingTag>
          );
        }

        if (block.type === "quote") {
          return (
            <blockquote key={`${index}-quote`}>
              {renderInlineMarkdown(block.content)}
            </blockquote>
          );
        }

        if (block.type === "list") {
          const ListTag = block.ordered ? "ol" : "ul";
          return (
            <ListTag key={`${index}-list`}>
              {block.items.map((item, itemIndex) => (
                <li key={`${itemIndex}-${item}`}>{renderInlineMarkdown(item)}</li>
              ))}
            </ListTag>
          );
        }

        if (block.type === "table") {
          const [header = [], ...rows] = block.rows;
          return (
            <div className="markdown-table-wrap" key={`${index}-table`}>
              <table>
                <thead>
                  <tr>
                    {header.map((cell) => (
                      <th key={cell}>{renderInlineMarkdown(cell)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row, rowIndex) => (
                    <tr key={`${rowIndex}-${row.join("-")}`}>
                      {row.map((cell, cellIndex) => (
                        <td key={`${cellIndex}-${cell}`}>
                          {renderInlineMarkdown(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }

        return <p key={`${index}-paragraph`}>{renderInlineMarkdown(block.content)}</p>;
      })}
    </div>
  );
}

function SourceCitations({ onOpenSourceDetails, sources }) {
  if (!sources?.length) {
    return null;
  }

  return (
    <div className="source-citations" aria-label="Sources used">
      {sources.map((source) => {
        const normalized = normalizeSource(source);
        return (
          <Tooltip
            content={`${normalized.path}: ${normalized.snippet}`}
            key={normalized.path}
          >
            <SourceChip
              aria-label={`Open source ${normalized.path}`}
              className="citation-chip"
              onClick={() => onOpenSourceDetails?.(normalized.path)}
              type="button"
            >
              {normalized.label}
            </SourceChip>
          </Tooltip>
        );
      })}
    </div>
  );
}

function DotsIcon() {
  return (
    <svg aria-hidden="true" className="message-actions-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M6.75 12h.01M12 12h.01M17.25 12h.01"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="3"
      />
    </svg>
  );
}

function MessageActionMenu({ content, filename, onDelete }) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    function handlePointerDown(event) {
      if (!menuRef.current?.contains(event.target)) {
        setOpen(false);
      }
    }

    function handleKeyDown(event) {
      if (event.key === "Escape") {
        setOpen(false);
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  function runAction(callback) {
    callback?.();
    setOpen(false);
  }

  return (
    <div className="message-action-menu" ref={menuRef}>
      <button
        aria-expanded={open}
        aria-haspopup="menu"
        aria-label="Open message actions"
        className="message-action-trigger"
        onClick={() => setOpen((current) => !current)}
        type="button"
      >
        <DotsIcon />
      </button>
      {open && (
        <div className="message-action-popover" role="menu">
          <button onClick={() => runAction(() => copyText(content))} role="menuitem" type="button">
            Copy
          </button>
          <button
            onClick={() => runAction(() => exportMarkdown(filename, content))}
            role="menuitem"
            type="button"
          >
            Export
          </button>
          <button
            className="message-action-popover__danger"
            onClick={() => runAction(onDelete)}
            role="menuitem"
            type="button"
          >
            Delete
          </button>
        </div>
      )}
    </div>
  );
}

function UserMessage({ message, onDelete }) {
  return (
    <article className="conversation-message conversation-message--user">
      <div className="message-row message-row--user">
        <div className="message-content message-content--user">
          <div className="message-meta">
            <span className="message-avatar">You</span>
            <time>{formatMessageTime(message.createdAt)}</time>
          </div>
          <div className="user-message__bubble">
            <p>{message.content}</p>
          </div>
        </div>
        <MessageActionMenu
          content={message.content}
          filename="user-message.md"
          onDelete={onDelete}
        />
      </div>
    </article>
  );
}

function AssistantMessage({
  activeChat,
  index,
  message,
  onDelete,
  onOpenSourceDetails,
}) {
  const shouldAnimate = isRecentAssistantMessage(message);
  const { isStreaming, visibleContent } = useProgressiveText(message.content, shouldAnimate);
  const fullContentBlocks = parseContentBlocks(message.content);
  const contentBlocks = parseContentBlocks(visibleContent);
  const sources = message.sources || [];
  const generationTime = formatGenerationTime(message.generationTimeMs);
  const tokenCount = estimateTokenCount(message.content);
  const isLongResponse = message.content.length > 1800 || fullContentBlocks.length > 5;
  const [expanded, setExpanded] = useState(!isLongResponse);

  useEffect(() => {
    setExpanded(!isLongResponse);
  }, [isLongResponse, message.content]);

  const isCollapsed = isLongResponse && !expanded && !isStreaming;
  const cardClassName = [
    "assistant-response-card",
    isStreaming ? "assistant-response-card--streaming" : "",
  ]
    .filter(Boolean)
    .join(" ");
  const bodyClassName = [
    "assistant-message__body",
    isCollapsed ? "assistant-message__body--collapsed" : "",
    isStreaming ? "assistant-message__body--streaming" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <article className="conversation-message conversation-message--assistant">
      <div className="message-row message-row--assistant">
        <div
          aria-label="Assistant response"
          className={cardClassName}
          tabIndex={0}
        >
          <header className="assistant-response-card__header">
            <div>
              <span className="message-avatar message-avatar--assistant">Assistant</span>
              <time>{formatMessageTime(message.createdAt)}</time>
              {isStreaming && <span className="assistant-live-status">Streaming locally</span>}
            </div>
            <div className="assistant-response-card__meta" aria-label="Response metadata">
              <span>{generationTime}</span>
              <span>{tokenCount.toLocaleString()} est. tokens</span>
            </div>
          </header>

          <div className={bodyClassName} aria-live={isStreaming ? "polite" : undefined}>
            {isStreaming && !visibleContent && (
              <div className="assistant-token-warmup" aria-label="Preparing response">
                <span />
                <span />
                <span />
              </div>
            )}
            {contentBlocks.map((block, blockIndex) =>
              block.type === "code" ? (
                <CodeBlock block={block} key={`${blockIndex}-code`} />
              ) : (
                <div className="assistant-message__text" key={`${blockIndex}-text`}>
                  <MarkdownContent content={block.content} />
                </div>
              ),
            )}
            {isStreaming && visibleContent && (
              <span className="assistant-stream-cursor" aria-hidden="true" />
            )}

            <SourceCitations onOpenSourceDetails={onOpenSourceDetails} sources={sources} />
          </div>

          {isLongResponse && !isStreaming && (
            <Button
              aria-expanded={expanded}
              className="assistant-expand-button"
              onClick={() => setExpanded((current) => !current)}
              type="button"
              variant="ghost"
            >
              {expanded ? "Collapse response" : "Show full response"}
            </Button>
          )}
        </div>
        <MessageActionMenu
          content={message.content}
          filename={`${activeChat.title.replace(/[^a-z0-9_-]+/gi, "-").toLowerCase() || "response"}-${index + 1}.md`}
          onDelete={onDelete}
        />
      </div>
    </article>
  );
}

function AssistantLoadingMessage() {
  return (
    <article className="conversation-message conversation-message--assistant conversation-message--loading">
      <div className="assistant-response-card">
        <header className="assistant-response-card__header">
          <div>
            <span className="message-avatar message-avatar--assistant">Assistant</span>
            <span className="reading-context">Thinking...</span>
          </div>
        </header>
        <div className="assistant-message__body">
          <div className="thinking-state" aria-label="Assistant is responding">
            <div className="thinking-orbit" aria-hidden="true">
              <span />
              <span />
              <span />
            </div>
            <div>
              <strong>Preparing response</strong>
              <small>Asking the local model and preparing the first token.</small>
            </div>
          </div>
        </div>
      </div>
    </article>
  );
}

function MessageList({
  activeChat,
  isSending,
  onDeleteMessage,
  onOpenSourceDetails,
}) {
  const messages = activeChat?.messages || [];

  return (
    <div className="message-stack">
      {messages.map((item, index) =>
        item.role === "user" ? (
          <UserMessage
            key={`${activeChat.id}-${item.role}-${index}`}
            message={item}
            onDelete={() => onDeleteMessage(index)}
          />
        ) : (
          <AssistantMessage
            activeChat={activeChat}
            index={index}
            key={`${activeChat.id}-${item.role}-${index}`}
            message={item}
            onDelete={() => onDeleteMessage(index)}
            onOpenSourceDetails={onOpenSourceDetails}
          />
        ),
      )}
      {isSending && <AssistantLoadingMessage />}
    </div>
  );
}

function Conversation({
  activeChat,
  isSending,
  onDeleteMessage,
  onOpenSourceDetails,
}) {
  const scrollRef = useRef(null);
  const shouldStickToBottomRef = useRef(true);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);
  const messages = activeChat?.messages || [];
  const hasMessages = messages.length > 0;

  function scrollToBottom(behavior = "smooth") {
    const node = scrollRef.current;
    if (!node) {
      return;
    }
    const reducedMotionQuery =
      typeof window.matchMedia === "function"
        ? window.matchMedia("(prefers-reduced-motion: reduce)")
        : null;
    const prefersReducedMotion = Boolean(reducedMotionQuery?.matches);
    const scrollBehavior = prefersReducedMotion ? "auto" : behavior;
    if (typeof node.scrollTo === "function") {
      node.scrollTo({ top: node.scrollHeight, behavior: scrollBehavior });
      return;
    }
    node.scrollTop = node.scrollHeight;
  }

  function updateScrollState() {
    const node = scrollRef.current;
    if (!node) {
      return;
    }

    const distanceFromBottom = node.scrollHeight - node.scrollTop - node.clientHeight;
    const isNearBottom = distanceFromBottom < 140;
    shouldStickToBottomRef.current = isNearBottom;
    setShowJumpToBottom(!isNearBottom && hasMessages);
  }

  useEffect(() => {
    if (shouldStickToBottomRef.current) {
      window.requestAnimationFrame(() => scrollToBottom("smooth"));
    }
  }, [messages.length, isSending]);

  return (
    <section
      className={`conversation ${hasMessages ? "" : "conversation--empty"}`}
      aria-busy={isSending}
      aria-label="Conversation"
    >
      <div
        className="conversation-scroll"
        aria-live="polite"
        onScroll={updateScrollState}
        ref={scrollRef}
      >
        {!hasMessages ? (
          <EmptyChatLanding />
        ) : (
          <MessageList
            activeChat={activeChat}
            isSending={isSending}
            onDeleteMessage={onDeleteMessage}
            onOpenSourceDetails={onOpenSourceDetails}
          />
        )}

        {!hasMessages && isSending && <AssistantLoadingMessage />}
      </div>
      {showJumpToBottom && (
        <Button
          className="jump-to-bottom-button"
          onClick={() => scrollToBottom("smooth")}
          type="button"
          variant="secondary"
        >
          Jump to bottom
        </Button>
      )}
    </section>
  );
}

export default Conversation;
