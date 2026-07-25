import type { RefObject } from "react"
import { CenteredModal } from "../../components/CenteredModal"
import type { Conversation } from "./types"

export function DeleteConversationModal({
  conversation,
  cancelButtonRef,
  returnFocusRef,
  pending,
  error,
  onCancel,
  onConfirm,
}: {
  conversation?: Conversation
  cancelButtonRef: RefObject<HTMLButtonElement | null>
  returnFocusRef: RefObject<HTMLTextAreaElement | null>
  pending: boolean
  error: string
  onCancel: () => void
  onConfirm: () => void
}) {
  if (!conversation) return null

  return (
    <CenteredModal
      ariaLabelledBy="delete-conversation-title"
      initialFocusRef={cancelButtonRef}
      returnFocusRef={returnFocusRef}
      onRequestClose={pending ? () => undefined : onCancel}
      maxWidth={420}
    >
      <div className="delete-conversation-dialog">
        <div className="delete-conversation-icon" aria-hidden="true">
          !
        </div>
        <div>
          <h2 id="delete-conversation-title">Delete conversation?</h2>
          <p>
            “{conversation.title}” will be removed from your chat list. This
            cannot be undone in this demo.
          </p>
        </div>
      </div>
      {error && (
        <p className="operation-error" role="alert">
          {error}
        </p>
      )}
      <div className="delete-conversation-actions">
        <button
          ref={cancelButtonRef}
          type="button"
          onClick={onCancel}
          disabled={pending}
        >
          Cancel
        </button>
        <button
          type="button"
          className="delete-conversation-confirm"
          onClick={onConfirm}
          disabled={pending}
        >
          {pending ? "Deleting…" : "Delete conversation"}
        </button>
      </div>
    </CenteredModal>
  )
}
