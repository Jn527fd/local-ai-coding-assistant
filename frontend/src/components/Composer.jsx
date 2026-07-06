import { useMemo, useRef, useState } from "react";

import { Button, Textarea } from "./ui.jsx";

const MAX_IMAGE_ATTACHMENTS = 4;
const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const IMAGE_MIME_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);

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

function ImageIcon() {
  return (
    <svg aria-hidden="true" className="composer-plus-icon" fill="none" viewBox="0 0 24 24">
      <path
        d="M4 6.5A2.5 2.5 0 0 1 6.5 4h11A2.5 2.5 0 0 1 20 6.5v11a2.5 2.5 0 0 1-2.5 2.5h-11A2.5 2.5 0 0 1 4 17.5v-11Z"
        stroke="currentColor"
        strokeWidth="2"
      />
      <path
        d="m7 16 3.2-3.2a1 1 0 0 1 1.4 0L13 14.2l2.3-2.3a1 1 0 0 1 1.4 0L20 15.2M8.5 8.5h.01"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2"
      />
    </svg>
  );
}

function bytesToBase64(bytes) {
  let binary = "";
  bytes.forEach((byte) => {
    binary += String.fromCharCode(byte);
  });
  return btoa(binary);
}

async function imageFileToAttachment(file) {
  if (!IMAGE_MIME_TYPES.has(file.type)) {
    throw new Error("Attach PNG, JPEG, or WebP images for vision chat.");
  }
  if (file.size > MAX_IMAGE_BYTES) {
    throw new Error("Image attachments must be 5 MiB or smaller.");
  }
  const buffer = await readFileAsArrayBuffer(file);
  return {
    name: file.name || "image",
    mimeType: file.type,
    size: file.size,
    data: bytesToBase64(new Uint8Array(buffer)),
  };
}

function readFileAsArrayBuffer(file) {
  if (typeof file.arrayBuffer === "function") {
    return file.arrayBuffer();
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error("Image read failed."));
    reader.readAsArrayBuffer(file);
  });
}

function Composer({
  activeChat,
  composerRef,
  documentError = "",
  documentJobProgress = null,
  documents = [],
  isUploadingDocument = false,
  isSending,
  message,
  onMessageChange,
  onSendMessage,
  onUploadDocument,
}) {
  const fileInputRef = useRef(null);
  const imageInputRef = useRef(null);
  const [focused, setFocused] = useState(false);
  const [imageAttachments, setImageAttachments] = useState([]);
  const [imageError, setImageError] = useState("");
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

  const composerStatus = useMemo(() => {
    if (isSending) {
      return "Sending message. Assistant response is streaming.";
    }
    if (documentJobProgress) {
      return `${documentJobProgress.label}: ${documentJobProgress.progress || 0} percent. ${documentJobProgress.message}`;
    }
    if (isUploadingDocument) {
      return "Processing document.";
    }
    if (documentError) {
      return `Document error: ${documentError}`;
    }
    return "";
  }, [
    documentError,
    documentJobProgress,
    isSending,
    isUploadingDocument,
  ]);

  async function handleSubmit(event) {
    event.preventDefault();
    const trimmed = message.trim();
    if (!trimmed || isSending) {
      return;
    }

    onMessageChange("");
    setSlashOpen(false);

    const didSend = await onSendMessage(trimmed, imageAttachments);

    if (!didSend) {
      onMessageChange(trimmed);
      return;
    }
    setImageAttachments([]);
    setImageError("");

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

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !onUploadDocument) {
      return;
    }
    await onUploadDocument(file);
  }

  async function handleImageChange(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) {
      return;
    }
    setImageError("");
    try {
      const remainingSlots = MAX_IMAGE_ATTACHMENTS - imageAttachments.length;
      if (files.length > remainingSlots) {
        throw new Error(`Attach up to ${MAX_IMAGE_ATTACHMENTS} images per message.`);
      }
      const nextAttachments = await Promise.all(files.map(imageFileToAttachment));
      setImageAttachments((current) => [...current, ...nextAttachments]);
    } catch (error) {
      setImageError(error.message || "Image attachment failed.");
    }
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
      aria-busy={isSending || isUploadingDocument}
      aria-label="Chat composer"
      className={`composer smart-composer ${focused ? "smart-composer--focused" : ""}`}
      onSubmit={handleSubmit}
    >
      <div aria-live="polite" className="sr-only" role="status">
        {composerStatus}
      </div>
      <div className="smart-composer__input-shell">
        <label className="sr-only" htmlFor="chat-message">
          Message assistant
        </label>
        <button
          aria-label="Attach document"
          className="composer-attach-button"
          disabled={!activeChat || isUploadingDocument}
          onClick={() => fileInputRef.current?.click()}
          title="Attach document"
          type="button"
        >
          <PlusIcon />
        </button>
        <input
          accept=".txt,.md,.pdf,.docx,.html,.htm,.csv,.tsv"
          aria-label="Document upload"
          className="composer-file-input"
          disabled={!activeChat || isUploadingDocument}
          onChange={handleFileChange}
          ref={fileInputRef}
          type="file"
        />
        <button
          aria-label="Attach image"
          className="composer-attach-button composer-attach-button--image"
          disabled={!activeChat || isSending}
          onClick={() => imageInputRef.current?.click()}
          title="Attach image"
          type="button"
        >
          <ImageIcon />
        </button>
        <input
          accept="image/png,image/jpeg,image/webp"
          aria-label="Image upload"
          className="composer-file-input"
          disabled={!activeChat || isSending}
          multiple
          onChange={handleImageChange}
          ref={imageInputRef}
          type="file"
        />
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

        {(imageAttachments.length > 0 || imageError) && (
          <div
            aria-label="Image attachments"
            aria-live="polite"
            className="image-attachment-tray"
            role="status"
          >
            {imageError && (
              <span className="document-chip document-chip--error">
                {imageError}
              </span>
            )}
            {imageAttachments.map((image) => (
              <span className="document-chip document-chip--processed" key={`${image.name}-${image.size}`}>
                <strong>{image.name}</strong>
                <small>Image attached</small>
                <Button
                  aria-label={`Remove image ${image.name}`}
                  className="document-chip__action"
                  onClick={() =>
                    setImageAttachments((current) =>
                      current.filter((item) => item !== image),
                    )
                  }
                  type="button"
                  variant="plain"
                >
                  Remove
                </Button>
              </span>
            ))}
          </div>
        )}

        {(documents.length > 0 ||
          documentError ||
          isUploadingDocument ||
          documentJobProgress) && (
          <div
            aria-label="Document processing status"
            aria-live="polite"
            className="document-tray"
            role="status"
          >
            {isUploadingDocument && (
              <span className="document-chip document-chip--working">
                Processing document...
              </span>
            )}
            {documentJobProgress && (
              <span
                aria-label={`${documentJobProgress.label} ${documentJobProgress.progress || 0} percent`}
                aria-valuemax="100"
                aria-valuemin="0"
                aria-valuenow={documentJobProgress.progress || 0}
                className="document-chip document-chip--working"
                role="progressbar"
              >
                <strong>{documentJobProgress.label}</strong>
                <small>
                  {documentJobProgress.progress || 0}% - {documentJobProgress.message}
                </small>
              </span>
            )}
            {documentError && (
              <span className="document-chip document-chip--error">
                {documentError}
              </span>
            )}
            {documents.map((document) => (
              <span
                className={`document-chip document-chip--${document.status || "uploaded"}`}
                key={document.documentId}
                title={document.originalFilename || "Document"}
              >
                <strong>{document.originalFilename || "Document"}</strong>
              </span>
            ))}
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
