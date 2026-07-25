import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import {
  createMockServices,
  type MockServiceBundle,
} from "../../services/mock/createMockServices"
import { DiagnosticsPage } from "./DiagnosticsPage"

describe("DiagnosticsPage", () => {
  let bundle: MockServiceBundle
  let createObjectUrl: ReturnType<typeof vi.fn>
  let revokeObjectUrl: ReturnType<typeof vi.fn>

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    bundle = createMockServices()
    bundle.control.setLatency(0)
    createObjectUrl = vi.fn(() => "blob:diagnostics")
    revokeObjectUrl = vi.fn()
    vi.stubGlobal("URL", {
      createObjectURL: createObjectUrl,
      revokeObjectURL: revokeObjectUrl,
    })
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it("loads diagnostics status and preserves redaction messaging", async () => {
    render(
      <MemoryRouter>
        <DiagnosticsPage diagnosticsService={bundle.services.diagnostics} />
      </MemoryRouter>,
    )

    expect(await screen.findByText("Runtime")).toBeInTheDocument()
    expect(screen.getByText("Models")).toBeInTheDocument()
    expect(screen.getByText("Documents")).toBeInTheDocument()
    expect(screen.getByText("Retrieval")).toBeInTheDocument()
    expect(screen.getByText("Jobs")).toBeInTheDocument()
    expect(
      screen.getByText(/Support bundles are redacted by default/),
    ).toBeInTheDocument()
    expect(screen.getByText(/"mode": "mock"/)).toBeInTheDocument()
  })

  it("exports a redacted support bundle", async () => {
    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined)
    const user = userEvent.setup()
    render(
      <MemoryRouter>
        <DiagnosticsPage diagnosticsService={bundle.services.diagnostics} />
      </MemoryRouter>,
    )

    await screen.findByText("Runtime")
    await user.click(screen.getByRole("button", { name: "Export bundle" }))

    expect(
      await screen.findByText("Redacted support bundle exported."),
    ).toBeInTheDocument()
    expect(createObjectUrl).toHaveBeenCalledWith(expect.any(Blob))
    expect(clickSpy).toHaveBeenCalled()
    expect(revokeObjectUrl).toHaveBeenCalledWith("blob:diagnostics")
    clickSpy.mockRestore()
  })
})
