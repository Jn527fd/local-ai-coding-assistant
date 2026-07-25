import type { RefObject } from "react"
import { CenteredModal } from "./CenteredModal"

export interface ConfirmationRequest {
  title: string
  description: string
  confirmLabel: string
  tone?: "danger" | "primary"
  onConfirm: () => void | Promise<void>
}

export function ConfirmationModal({
  request,
  pending,
  error,
  cancelButtonRef,
  onCancel,
  onConfirm,
}: {
  request: ConfirmationRequest | null
  pending: boolean
  error: string
  cancelButtonRef: RefObject<HTMLButtonElement | null>
  onCancel: () => void
  onConfirm: () => void
}) {
  if (!request) return null

  return (
    <CenteredModal
      ariaLabelledBy="confirmation-title"
      initialFocusRef={cancelButtonRef}
      onRequestClose={pending ? () => undefined : onCancel}
      maxWidth={440}
    >
      <div className="confirmation-dialog">
        <h2 id="confirmation-title">{request.title}</h2>
        <p>{request.description}</p>
        {error && (
          <p className="operation-error" role="alert">
            {error}
          </p>
        )}
        <div className="confirmation-actions">
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
            onClick={onConfirm}
            disabled={pending}
            className={
              request.tone === "danger" ? "danger-action" : "primary-action"
            }
          >
            {pending ? "Working…" : request.confirmLabel}
          </button>
        </div>
      </div>
    </CenteredModal>
  )
}
