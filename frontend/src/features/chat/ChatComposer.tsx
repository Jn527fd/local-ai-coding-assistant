import type { ChangeEvent, RefObject } from "react"
import type { ChatAttachment } from "../../domain/models"

export interface ComposerAttachmentDraft extends ChatAttachment {
  file: File
  progress: number
  attempts: number
}

export function ChatComposer({
  inputValue,
  onInputChange,
  onSend,
  isSending,
  attachments,
  attachmentError,
  onFilesSelected,
  onRemoveAttachment,
  onRetryAttachment,
  fileInputRef,
  inputRef,
  sendOnEnter = true,
  onComposerClick,
}: {
  inputValue: string
  onInputChange: (value: string) => void
  onSend: () => void
  isSending: boolean
  attachments: ComposerAttachmentDraft[]
  attachmentError: string
  onFilesSelected: (files: File[]) => void
  onRemoveAttachment: (attachmentId: string) => void
  onRetryAttachment: (attachmentId: string) => void
  fileInputRef: RefObject<HTMLInputElement | null>
  inputRef: RefObject<HTMLTextAreaElement | null>
  sendOnEnter?: boolean
  onComposerClick?: () => void
}) {
  const canSend =
    !isSending &&
    (inputValue.trim().length > 0 ||
      attachments.some((attachment) => attachment.status === "ready"))

  const handleFiles = (event: ChangeEvent<HTMLInputElement>) => {
    onFilesSelected(Array.from(event.target.files ?? []))
    event.target.value = ""
  }

  return (
    <div
      className="chat-composer-shell"
      role="region"
      aria-label="Message composer"
    >
      {(attachments.length > 0 || attachmentError) && (
        <div className="composer-attachments-panel">
          {attachments.map((attachment) => (
            <div className="composer-attachment" key={attachment.id}>
              {attachment.mediaType.startsWith("image/") && attachment.url ? (
                <img src={attachment.url} alt="" />
              ) : (
                <span className="composer-file-icon" aria-hidden="true">
                  📎
                </span>
              )}
              <div>
                <strong title={attachment.filename}>
                  {attachment.filename}
                </strong>
                <span>
                  {attachment.status === "uploading"
                    ? `Preparing ${attachment.progress}%`
                    : attachment.status === "failed"
                      ? attachment.error
                      : `${formatFileSize(attachment.size)} ready`}
                </span>
                {attachment.status === "uploading" && (
                  <progress value={attachment.progress} max={100} />
                )}
              </div>
              {attachment.status === "failed" && (
                <button
                  type="button"
                  onClick={() => onRetryAttachment(attachment.id)}
                >
                  Retry
                </button>
              )}
              <button
                type="button"
                aria-label={`Remove ${attachment.filename}`}
                onClick={() => onRemoveAttachment(attachment.id)}
              >
                ×
              </button>
            </div>
          ))}
          {attachmentError && (
            <p className="operation-error" role="alert">
              {attachmentError}
            </p>
          )}
        </div>
      )}

      <div className="chat-composer" onClick={onComposerClick}>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,application/pdf,text/plain,text/markdown,text/csv"
          onChange={handleFiles}
          style={{ display: "none" }}
          multiple
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          title="Attach files or images"
          aria-label="Attach files or images"
          className="composer-icon-button"
          disabled={isSending || attachments.length >= 5}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
            <path
              d="M12 5v14M5 12h14"
              stroke="currentColor"
              strokeWidth="2.2"
              strokeLinecap="round"
            />
          </svg>
        </button>

        <textarea
          ref={inputRef}
          rows={1}
          value={inputValue}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && sendOnEnter) {
              event.preventDefault()
              if (canSend) {
                onSend()
              }
            }
          }}
          placeholder="Ask Away…"
          aria-label="Message"
        />

        <button
          type="button"
          title="Dictation is not available in this frontend demo"
          aria-label="Dictation unavailable"
          className="composer-icon-button"
          disabled
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <rect
              x="9"
              y="2"
              width="6"
              height="13"
              rx="3"
              stroke="currentColor"
              strokeWidth="1.8"
            />
            <path
              d="M5 10a7 7 0 0 0 14 0M12 19v3"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
            />
          </svg>
        </button>

        <button
          type="button"
          onClick={canSend ? onSend : undefined}
          title={
            canSend
              ? isSending
                ? "Sending"
                : "Send"
              : "Voice chat is not available in this frontend demo"
          }
          aria-label={canSend ? "Send" : "Voice chat unavailable"}
          className={canSend ? "composer-send-button" : "composer-icon-button"}
          disabled={!canSend}
        >
          {isSending ? (
            <span className="button-spinner" aria-hidden="true" />
          ) : canSend ? (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path
                d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          ) : (
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
              <path
                d="M22 16.92v3a2 2 0 0 1-2.18 2 19.8 19.8 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.8 19.8 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          )}
        </button>
      </div>
    </div>
  )
}

function formatFileSize(size: number) {
  if (size >= 1_000_000) return `${(size / 1_000_000).toFixed(1)} MB`
  return `${Math.max(1, Math.round(size / 1_000))} KB`
}
