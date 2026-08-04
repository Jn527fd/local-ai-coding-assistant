import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"
import {
  createMockServices,
  type MockServiceBundle,
} from "../../services/mock/createMockServices"
import type { ProfileService } from "../../services"
import { ProfilePage } from "./ProfilePage"

describe("ProfilePage", () => {
  let bundle: MockServiceBundle

  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    bundle = createMockServices()
    bundle.control.setLatency(0)
  })

  function renderProfile() {
    return render(
      <MemoryRouter>
        <ProfilePage profileService={bundle.services.profile} />
      </MemoryRouter>,
    )
  }

  it("loads editable and read-only local profile information", async () => {
    renderProfile()

    expect(screen.getByText("Loading your local profile")).toBeInTheDocument()
    expect(await screen.findByDisplayValue("Taylor Morgan")).toBeInTheDocument()
    expect(screen.getByLabelText("Handle")).toHaveValue("taylor.morgan")
    expect(screen.getByText("usr-local-7f2a91")).toBeInTheDocument()
    expect(screen.getByText("Stored on this local server")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled()
  })

  it("validates edits, tracks dirty state, resets, and saves successfully", async () => {
    const user = userEvent.setup()
    renderProfile()
    const displayName = await screen.findByLabelText("Display name")
    const handle = screen.getByLabelText("Handle")
    const save = screen.getByRole("button", { name: "Save changes" })

    await user.clear(displayName)
    expect(screen.getByText("Display name is required.")).toBeInTheDocument()
    expect(save).toBeDisabled()
    await user.type(displayName, "Morgan Lee")
    await user.clear(handle)
    await user.type(handle, "not allowed!")
    expect(screen.getByText(/Use only letters/)).toBeInTheDocument()
    await user.clear(handle)
    await user.type(handle, "morgan_lee")
    expect(save).toBeEnabled()

    await user.click(screen.getByRole("button", { name: "Reset" }))
    expect(displayName).toHaveValue("Taylor Morgan")
    expect(save).toBeDisabled()

    await user.clear(displayName)
    await user.type(displayName, "Morgan Lee")
    await user.click(save)
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Profile changes saved.",
    )
    expect(save).toBeDisabled()
  })

  it("preserves the draft and shows a save error", async () => {
    const user = userEvent.setup()
    bundle.control.failNext("profile.update")
    renderProfile()
    const displayName = await screen.findByLabelText("Display name")
    await user.clear(displayName)
    await user.type(displayName, "Unsaved Name")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Controlled mock failure for profile.update",
    )
    expect(displayName).toHaveValue("Unsaved Name")
    expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled()
  })

  it("offers the export-only profile action", async () => {
    const user = userEvent.setup()
    const downloadClick = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined)
    renderProfile()
    await screen.findByDisplayValue("Taylor Morgan")

    const exportButton = screen.getByRole("button", {
      name: "Export my data",
    })
    expect(exportButton).toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: "Delete local profile" }),
    ).not.toBeInTheDocument()

    await user.click(exportButton)
    expect(downloadClick).toHaveBeenCalledOnce()
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Your profile export is ready.",
    )
  })

  it("offers recovery when profile loading fails", async () => {
    bundle.control.failNext("profile.load")
    renderProfile()

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Controlled mock failure for profile.load",
    )
    await userEvent.click(screen.getByRole("button", { name: "Try again" }))
    expect(await screen.findByDisplayValue("Taylor Morgan")).toBeInTheDocument()
  })

  it("disables avatar upload when the active profile service does not support it", async () => {
    const profileService: ProfileService = {
      ...bundle.services.profile,
      capabilities: { avatarUpload: false, persistence: "local" },
    }
    render(
      <MemoryRouter>
        <ProfilePage profileService={profileService} />
      </MemoryRouter>,
    )

    expect(await screen.findByDisplayValue("Taylor Morgan")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Change avatar" })).toBeDisabled()
    expect(
      screen.getByText(
        "Avatar upload is not supported by the current backend.",
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(/Editable profile\s+preferences are browser-local/),
    ).toBeInTheDocument()
  })
})
