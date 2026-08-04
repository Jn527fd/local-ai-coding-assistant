import { createRef, useState } from "react"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { SystemPromptModal } from "./SystemPromptModal"

function PromptHarness() {
  const [draft, setDraft] = useState("Saved prompt")
  const [saved, setSaved] = useState("Saved prompt")
  const contextButtonRef = createRef<HTMLButtonElement>()
  return (
    <>
      <button ref={contextButtonRef}>Context</button>
      <SystemPromptModal
        open
        contextButtonRef={contextButtonRef}
        systemPromptRef={createRef<HTMLTextAreaElement>()}
        closeContextModal={vi.fn()}
        draftSystemPrompt={draft}
        setDraftSystemPrompt={setDraft}
        promptFileRef={createRef<HTMLInputElement>()}
        importModelFile={vi.fn()}
        promptFileName={null}
        setPromptFileName={vi.fn()}
        promptFileError=""
        setPromptFileError={vi.fn()}
        savedSystemPrompt={saved}
        hasUnsavedPrompt={draft !== saved}
        isSavingPrompt={false}
        clearSystemPrompt={() => setDraft("")}
        saveSystemPrompt={() => setSaved(draft)}
      />
    </>
  )
}

describe("SystemPromptModal", () => {
  it("distinguishes saved and draft prompt state", async () => {
    const user = userEvent.setup()
    render(<PromptHarness />)
    const editor = screen.getByLabelText("System prompt")
    await waitFor(() => expect(editor).toHaveFocus())
    expect(screen.getByRole("button", { name: "Save prompt" })).toBeDisabled()
    await user.clear(editor)
    await user.type(editor, "Draft prompt")
    expect(screen.getByText("12 characters")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Save prompt" })).toBeEnabled()
    await user.click(screen.getByRole("button", { name: "Save prompt" }))
    expect(screen.getByRole("button", { name: "Save prompt" })).toBeDisabled()
  })
})
