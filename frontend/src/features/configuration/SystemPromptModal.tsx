import type { ChangeEvent, Dispatch, RefObject, SetStateAction } from "react"
import { CenteredModal } from "../../components/CenteredModal"

export function SystemPromptModal({
  open,
  contextButtonRef,
  systemPromptRef,
  closeContextModal,
  draftSystemPrompt,
  setDraftSystemPrompt,
  promptFileRef,
  importModelFile,
  promptFileName,
  setPromptFileName,
  promptFileError,
  setPromptFileError,
  savedSystemPrompt,
  hasUnsavedPrompt,
  isSavingPrompt,
  clearSystemPrompt,
  saveSystemPrompt,
}: {
  open: boolean
  contextButtonRef: RefObject<HTMLButtonElement | null>
  systemPromptRef: RefObject<HTMLTextAreaElement | null>
  closeContextModal: () => void
  draftSystemPrompt: string
  setDraftSystemPrompt: Dispatch<SetStateAction<string>>
  promptFileRef: RefObject<HTMLInputElement | null>
  importModelFile: (event: ChangeEvent<HTMLInputElement>) => void
  promptFileName: string | null
  setPromptFileName: Dispatch<SetStateAction<string | null>>
  promptFileError: string
  setPromptFileError: Dispatch<SetStateAction<string>>
  savedSystemPrompt: string
  hasUnsavedPrompt: boolean
  isSavingPrompt: boolean
  clearSystemPrompt: () => void
  saveSystemPrompt: () => void
}) {
  if (!open) return null

  return (
    <CenteredModal
      ariaLabelledBy="context-modal-title"
      initialFocusRef={systemPromptRef}
      returnFocusRef={contextButtonRef}
      onRequestClose={closeContextModal}
    >
      <div
        className="context-modal-header"
        style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 16,
          padding: "18px 20px 16px",
          borderBottom: "1px solid rgba(200,220,255,0.5)",
        }}
      >
        <div>
          <h2
            id="context-modal-title"
            style={{
              margin: 0,
              color: "#1a2340",
              fontSize: 17,
              lineHeight: 1.3,
            }}
          >
            Context / System Prompt
          </h2>
          <p style={{ margin: "4px 0 0", color: "#5b7392", fontSize: 12 }}>
            Applies to this conversation only
          </p>
        </div>
        <button
          type="button"
          aria-label="Close system prompt"
          onClick={closeContextModal}
          style={{
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "#5f7390",
            padding: 4,
            display: "flex",
            alignItems: "center",
          }}
        >
          <svg width="17" height="17" viewBox="0 0 24 24" fill="none">
            <path
              d="M18 6 6 18M6 6l12 12"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
            />
          </svg>
        </button>
      </div>

      <div
        className="context-modal-body"
        style={{ padding: "18px 20px", overflowY: "auto" }}
      >
        <p
          style={{
            margin: "0 0 14px",
            color: "#61799c",
            fontSize: 13,
            lineHeight: 1.55,
          }}
        >
          Set instructions that guide how the assistant should respond
          throughout this conversation.
        </p>
        <div className="context-prompt-controls">
          <label htmlFor="system-prompt">System prompt</label>
          <input
            ref={promptFileRef}
            type="file"
            onChange={importModelFile}
            className="context-prompt-file-input"
            aria-label="Choose a system prompt text file to import"
          />
          <button type="button" onClick={() => promptFileRef.current?.click()}>
            System prompt file
          </button>
        </div>
        <p className="context-prompt-file-help">
          Write instructions below, or upload a UTF-8 text file to fill the
          system prompt. This guides responses in this conversation only; it
          does not create or modify an Ollama model.
        </p>
        {promptFileName && (
          <div className="context-prompt-file-status" role="status">
            <span aria-hidden="true">Imported</span>
            <span title={promptFileName}>{promptFileName}</span>
            <button
              type="button"
              onClick={() => {
                setDraftSystemPrompt("")
                setPromptFileName(null)
              }}
              aria-label={`Remove imported ${promptFileName}`}
            >
              Remove
            </button>
          </div>
        )}
        {promptFileError && (
          <p className="context-prompt-file-error" role="alert">
            {promptFileError}
          </p>
        )}
        <textarea
          ref={systemPromptRef}
          id="system-prompt"
          value={draftSystemPrompt}
          onChange={(event) => {
            setDraftSystemPrompt(event.target.value)
            setPromptFileName(null)
            setPromptFileError("")
          }}
          placeholder="Example: You are a concise technical assistant. Ask clarifying questions before suggesting architectural changes."
          style={{
            width: "100%",
            minHeight: 220,
            maxHeight: "42vh",
            resize: "vertical",
            overflowY: "auto",
            boxSizing: "border-box",
            border: "1px solid rgba(157,190,235,0.72)",
            borderRadius: 10,
            padding: "12px 13px",
            background: "rgba(248,251,255,0.9)",
            color: "#1a2340",
            fontFamily: "inherit",
            fontSize: 13,
            lineHeight: 1.55,
            outline: "none",
          }}
        />
        <div
          style={{
            marginTop: 6,
            color: "#5f7390",
            fontSize: 11,
            textAlign: "right",
          }}
          aria-live="polite"
        >
          {draftSystemPrompt.length.toLocaleString()} characters
        </div>
      </div>

      <div
        className="context-modal-footer"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 12,
          padding: "14px 20px",
          borderTop: "1px solid rgba(200,220,255,0.5)",
          background: "rgba(248,251,255,0.72)",
        }}
      >
        <button
          type="button"
          onClick={clearSystemPrompt}
          disabled={!draftSystemPrompt && !savedSystemPrompt}
          style={{
            border: "none",
            background: "transparent",
            color:
              draftSystemPrompt || savedSystemPrompt ? "#d05252" : "#687b94",
            fontFamily: "inherit",
            fontSize: 13,
            fontWeight: 600,
            cursor:
              draftSystemPrompt || savedSystemPrompt
                ? "pointer"
                : "not-allowed",
            padding: "8px 0",
          }}
        >
          Clear prompt
        </button>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            onClick={closeContextModal}
            style={{
              padding: "9px 14px",
              borderRadius: 9,
              border: "1px solid rgba(190,210,238,0.85)",
              background: "white",
              color: "#526b8e",
              fontFamily: "inherit",
              fontSize: 13,
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={saveSystemPrompt}
            disabled={!hasUnsavedPrompt || isSavingPrompt}
            style={{
              minWidth: 102,
              padding: "9px 14px",
              borderRadius: 9,
              border: "none",
              background:
                hasUnsavedPrompt && !isSavingPrompt
                  ? "linear-gradient(135deg,#4f8ef7,#7b5ea7)"
                  : "#cbd7e8",
              color: "white",
              fontFamily: "inherit",
              fontSize: 13,
              fontWeight: 700,
              cursor:
                hasUnsavedPrompt && !isSavingPrompt ? "pointer" : "not-allowed",
              boxShadow:
                hasUnsavedPrompt && !isSavingPrompt
                  ? "0 4px 14px rgba(79,142,247,0.22)"
                  : "none",
            }}
          >
            {isSavingPrompt ? "Saving..." : "Save prompt"}
          </button>
        </div>
      </div>
    </CenteredModal>
  )
}
