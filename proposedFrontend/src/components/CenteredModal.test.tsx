import { createRef, useState } from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { CenteredModal } from "./CenteredModal"

function ModalHarness({ onClose = () => undefined }: { onClose?: () => void }) {
  const [open, setOpen] = useState(false)
  const triggerRef = createRef<HTMLButtonElement>()
  const inputRef = createRef<HTMLInputElement>()
  return (
    <>
      <button ref={triggerRef} onClick={() => setOpen(true)}>
        Open dialog
      </button>
      {open && (
        <CenteredModal
          ariaLabel="Test dialog"
          initialFocusRef={inputRef}
          returnFocusRef={triggerRef}
          onRequestClose={() => {
            onClose()
            setOpen(false)
          }}
        >
          <input ref={inputRef} aria-label="First field" />
          <button>Last action</button>
        </CenteredModal>
      )}
    </>
  )
}

describe("CenteredModal", () => {
  it("moves focus in, closes with Escape, and restores focus", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ModalHarness onClose={onClose} />)
    const trigger = screen.getByRole("button", { name: "Open dialog" })
    await user.click(trigger)
    await waitFor(() =>
      expect(screen.getByLabelText("First field")).toHaveFocus(),
    )

    await user.keyboard("{Escape}")

    expect(onClose).toHaveBeenCalledOnce()
    expect(trigger).toHaveFocus()
  })

  it("requests close from the backdrop", async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    render(<ModalHarness onClose={onClose} />)
    await user.click(screen.getByRole("button", { name: "Open dialog" }))
    await user.click(
      screen.getByRole("dialog", { name: "Test dialog" }).parentElement!,
    )
    expect(onClose).toHaveBeenCalledOnce()
  })
})
