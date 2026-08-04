import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { beforeEach, describe, expect, it } from "vitest"
import { SettingsPage } from "./SettingsPage"
import { DEFAULT_APP_SETTINGS, SETTINGS_STORAGE_KEY } from "./settingsStorage"

function renderSettingsPage() {
  return render(
    <MemoryRouter>
      <SettingsPage />
    </MemoryRouter>,
  )
}

describe("SettingsPage", () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.removeAttribute("data-theme")
    document.documentElement.removeAttribute("data-text-size")
    document.documentElement.style.removeProperty("font-size")
  })

  it("loads saved device settings and starts clean", () => {
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({
        ...DEFAULT_APP_SETTINGS,
        theme: "dark",
        textSize: "large",
      }),
    )

    renderSettingsPage()

    expect(screen.getByLabelText("Theme")).toHaveValue("dark")
    expect(screen.getByLabelText("Text size")).toHaveValue("large")
    expect(screen.getByRole("button", { name: "Save changes" })).toBeDisabled()
    expect(document.documentElement.dataset.theme).toBe("dark")
  })

  it("persists edited settings and reports success", async () => {
    const user = userEvent.setup()
    renderSettingsPage()

    await user.selectOptions(screen.getByLabelText("Theme"), "dark")
    expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled()

    await user.click(screen.getByRole("button", { name: "Save changes" }))

    expect(screen.getByRole("status")).toHaveTextContent("Settings saved.")
    expect(
      JSON.parse(localStorage.getItem(SETTINGS_STORAGE_KEY) ?? "{}"),
    ).toMatchObject({
      theme: "dark",
    })
    expect(document.documentElement.dataset.theme).toBe("dark")
  })

  it("requires confirmation before resetting saved settings", async () => {
    const user = userEvent.setup()
    localStorage.setItem(
      SETTINGS_STORAGE_KEY,
      JSON.stringify({ ...DEFAULT_APP_SETTINGS, sendOnEnter: false }),
    )
    renderSettingsPage()

    await user.click(screen.getByRole("button", { name: "Reset to defaults" }))
    expect(
      screen.getByRole("dialog", { name: "Reset settings to defaults?" }),
    ).toBeVisible()

    await user.click(screen.getByRole("button", { name: "Reset settings" }))

    expect(
      screen.getByRole("checkbox", { name: /Send messages with Enter/ }),
    ).toBeChecked()
    expect(screen.getByRole("status")).toHaveTextContent(
      "Settings reset to defaults.",
    )
  })
})
