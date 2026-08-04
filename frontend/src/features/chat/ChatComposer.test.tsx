import { render, screen } from "@testing-library/react"

import userEvent from "@testing-library/user-event"

import { describe, expect, it, vi } from "vitest"

import { ChatComposer } from "./ChatComposer"

describe("ChatComposer", () => {
  it("calls the composer click handler when the message box is interacted with", async () => {
    const user = userEvent.setup()

    const onComposerClick = vi.fn()

    render(
      <ChatComposer
        inputValue=""
        onInputChange={() => undefined}
        onSend={() => undefined}
        isSending={false}
        attachments={[]}
        attachmentError=""
        onFilesSelected={() => undefined}
        onRemoveAttachment={() => undefined}
        onRetryAttachment={() => undefined}
        fileInputRef={{ current: null }}
        inputRef={{ current: null }}
        sendOnEnter={true}
        onComposerClick={onComposerClick}
      />,
    )

    await user.click(screen.getByLabelText("Message"))

    expect(onComposerClick).toHaveBeenCalledTimes(1)
  })

  it("does not send on Enter when the send-on-enter setting is disabled", async () => {
    const user = userEvent.setup()

    const onSend = vi.fn()

    render(
      <ChatComposer
        inputValue=""
        onInputChange={() => undefined}
        onSend={onSend}
        isSending={false}
        attachments={[]}
        attachmentError=""
        onFilesSelected={() => undefined}
        onRemoveAttachment={() => undefined}
        onRetryAttachment={() => undefined}
        fileInputRef={{ current: null }}
        inputRef={{ current: null }}
        sendOnEnter={false}
      />,
    )

    const textarea = screen.getByLabelText("Message")

    await user.type(textarea, "hello{enter}")

    expect(onSend).not.toHaveBeenCalled()
  })
})
