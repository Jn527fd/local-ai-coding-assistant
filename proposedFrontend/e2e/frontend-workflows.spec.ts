import { expect, test, type Page } from "@playwright/test"
import AxeBuilder from "@axe-core/playwright"

async function signIn(page: Page) {
  await page.goto("/login")
  await page.getByLabel("Username").fill("test")
  await page.getByLabel("Password").fill("test")
  await page.getByRole("button", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/chat(?:\/|$)/)
  await expect(
    page.getByRole("textbox", { name: "Message", exact: true }),
  ).toBeEditable()
}

async function send(page: Page, message: string) {
  await page
    .getByRole("textbox", { name: "Message", exact: true })
    .fill(message)
  await page.getByRole("button", { name: "Send" }).click()
  await expect(
    page
      .getByLabel("Assistant message", { exact: true })
      .last()
      .getByText("Thanks for your message", { exact: false }),
  ).toBeVisible()
}

async function openSidebar(page: Page) {
  const open = page.getByRole("button", { name: "Open sidebar" })
  if (await open.isVisible()) await open.click()
  await expect(
    page.getByRole("button", { name: "Close sidebar" }),
  ).toBeVisible()
}

test.describe
  .serial("frontend handoff workflows", () => {
    test("signs in, restores the session, supports keyboard access, passes Axe, and signs out", async ({
      page,
    }) => {
      await page.goto("/login")
      await expect(page.getByLabel("Username")).toBeFocused()
      await page.keyboard.type("test")
      await page.keyboard.press("Tab")
      await page.keyboard.press("Tab")
      await page.keyboard.type("test")
      await page.keyboard.press("Enter")
      await expect(page).toHaveURL(/\/chat(?:\/|$)/)

      await page.reload()
      await expect(
        page.getByRole("textbox", { name: "Message", exact: true }),
      ).toBeEditable()
      const results = await new AxeBuilder({ page }).analyze()
      expect(results.violations).toEqual([])

      await page.getByRole("button", { name: "Open profile menu" }).click()
      await page.keyboard.press("End")
      await page.keyboard.press("Enter")
      await expect(page).toHaveURL(/\/login$/)
    })

    test("creates, switches, renames, searches, deletes, and recreates conversations without disabling the composer", async ({
      page,
    }) => {
      await signIn(page)
      await send(page, "Phase eight alpha")
      await openSidebar(page)

      await page
        .getByRole("button", { name: "Rename Phase eight alpha" })
        .click()
      const name = page.getByRole("textbox", {
        name: "Conversation name",
        exact: true,
      })
      await name.fill("   ")
      await expect(
        page.getByRole("button", { name: "Save conversation name" }),
      ).toBeDisabled()
      await name.fill("Renamed alpha")
      await page.getByRole("button", { name: "Save conversation name" }).click()
      await expect(
        page.getByRole("heading", { name: "Renamed alpha" }),
      ).toBeVisible()

      await page.getByRole("button", { name: "New Chat" }).click()
      await expect(page.getByText("New conversation started")).toBeVisible()
      await send(page, "Phase eight beta")
      await openSidebar(page)
      await page
        .getByRole("button", { name: /Renamed alpha/ })
        .first()
        .click()
      await expect(
        page.getByRole("heading", { name: "Renamed alpha" }),
      ).toBeVisible()

      await page.getByLabel("Filter conversation history").fill("beta")
      await expect(
        page.getByRole("button", { name: /^Phase eight beta / }),
      ).toBeVisible()
      await page.getByLabel("Filter conversation history").fill("")

      await openSidebar(page)
      await page.getByRole("button", { name: "Delete Renamed alpha" }).click()
      await page
        .getByRole("button", { name: "Delete conversation", exact: true })
        .click()
      await expect(page.getByRole("dialog")).toHaveCount(0)
      await expect(
        page.getByRole("textbox", { name: "Message", exact: true }),
      ).toBeEditable()
      await page
        .getByRole("textbox", { name: "Message", exact: true })
        .fill("Typed immediately after active deletion")
      await expect(
        page.getByRole("textbox", { name: "Message", exact: true }),
      ).toHaveValue("Typed immediately after active deletion")

      await page.getByRole("textbox", { name: "Message", exact: true }).fill("")
      await openSidebar(page)
      await page
        .getByRole("button", { name: "Delete Phase eight beta" })
        .click()
      await page
        .getByRole("button", { name: "Delete conversation", exact: true })
        .click()
      await expect(page.getByRole("dialog")).toHaveCount(0)
      await expect(
        page.getByRole("textbox", { name: "Message", exact: true }),
      ).toBeEditable()
      await send(page, "Created after deleting every chat")
      await openSidebar(page)
      await expect(
        page.getByRole("button", {
          name: /^Created after deleting every chat /,
        }),
      ).toBeVisible()

      const conversationUrl = page.url()
      await page.reload()
      await expect(page).toHaveURL(conversationUrl)
      await expect(
        page.getByRole("heading", {
          name: "Created after deleting every chat",
        }),
      ).toBeVisible()
      await expect(
        page
          .getByLabel("Your message", { exact: true })
          .getByText("Created after deleting every chat", { exact: true }),
      ).toBeVisible()
      await expect(
        page.getByRole("textbox", { name: "Message", exact: true }),
      ).toBeEditable()
    })

    test("shows pending/completed messages, recovers failures, and isolates conversation prompt and settings", async ({
      page,
    }) => {
      await signIn(page)
      await page
        .getByRole("textbox", { name: "Message", exact: true })
        .fill("[fail]")
      await page.getByRole("button", { name: "Send" }).click()
      await expect(
        page.getByRole("status").filter({ hasText: "Mock generation failed" }),
      ).toBeVisible()
      await page.getByRole("button", { name: "Retry" }).click()
      await expect(
        page
          .getByLabel("Assistant message", { exact: true })
          .getByText("Thanks for retrying", { exact: false }),
      ).toBeVisible()

      await page
        .getByRole("button", { name: "Context / system prompt" })
        .click()
      await page
        .getByRole("textbox", { name: "System prompt", exact: true })
        .fill("Only this conversation")
      await page.getByRole("button", { name: "Save prompt" }).click()
      await expect(page.getByRole("dialog")).toHaveCount(0)
      await expect(
        page.getByRole("button", { name: "Context / system prompt" }),
      ).toHaveAttribute("aria-expanded", "false")

      await page
        .getByRole("button", { name: "Temporary chat (not saved)" })
        .click()
      await expect(
        page.getByRole("button", { name: "Temporary chat (not saved)" }),
      ).toHaveAttribute("aria-pressed", "true")
      await page.getByRole("button", { name: "New Chat" }).click()
      await expect(page.getByText("New conversation started")).toBeVisible()
      await page
        .getByRole("button", { name: "Context / system prompt" })
        .click()
      await expect(
        page.getByRole("textbox", { name: "System prompt", exact: true }),
      ).toHaveValue("")
      await page.keyboard.press("Escape")
      await expect(
        page.getByRole("button", { name: "Temporary chat (not saved)" }),
      ).toHaveAttribute("aria-pressed", "false")
    })

    test("uploads, selects, and deletes a source", async ({ page }) => {
      await signIn(page)
      await page.getByRole("button", { name: "Sources" }).click()
      const fileInput = page
        .getByRole("dialog", { name: "Sources" })
        .locator('input[type="file"]')
      await fileInput.setInputFiles({
        name: "unsupported.exe",
        mimeType: "application/octet-stream",
        buffer: Buffer.from("invalid"),
      })
      await expect(page.getByRole("alert")).toContainText(
        "unsupported file type",
      )
      await fileInput.setInputFiles({
        name: "phase-eight-notes.txt",
        mimeType: "text/plain",
        buffer: Buffer.from("test source"),
      })
      await expect(
        page.getByText("phase-eight-notes.txt", { exact: true }),
      ).toBeVisible()
      await page
        .getByLabel("Use phase-eight-notes.txt for next message")
        .check()
      await expect(page.getByText("1 source selected")).toBeVisible()
      await page.getByLabel("Delete phase-eight-notes.txt").click()
      await page
        .getByRole("button", { name: /delete source/i })
        .last()
        .click()
      await expect(
        page.getByText("phase-eight-notes.txt", { exact: true }),
      ).toHaveCount(0)
    })

    test("completes email signup and exposes mocked failure responses", async ({
      page,
    }) => {
      await page.goto("/signup/email")
      await page.getByLabel("Email address").fill("wrong@example.com")
      await page.getByRole("button", { name: "Sign up" }).click()
      await expect(page.getByRole("alert")).toContainText("test@email.com")
      await page.getByLabel("Email address").fill("test@email.com")
      await page.getByRole("button", { name: "Sign up" }).click()
      await page.getByLabel("Verification code").fill("00000")
      await page.getByRole("button", { name: "Verify code" }).click()
      await expect(page.getByRole("alert")).toContainText("not correct")
      await page.getByLabel("Verification code").fill("12345")
      await page.getByRole("button", { name: "Verify code" }).click()
      await page.getByLabel("Create password").fill("Strong!123")
      await page.getByLabel("Confirm password").fill("Strong!123")
      await page.getByRole("button", { name: "Create account" }).click()
      await expect(
        page.getByText(/password created successfully/i),
      ).toBeVisible()
    })

    test("edits and reloads the routed export-only profile", async ({
      page,
    }) => {
      await signIn(page)
      await page.getByRole("button", { name: "Open profile menu" }).click()
      await page.getByRole("menuitem", { name: "Profile" }).click()
      await expect(page).toHaveURL(/\/profile$/)
      await expect(
        page.getByRole("heading", { name: "Profile", level: 1 }),
      ).toBeVisible()

      await page.locator('input[type="file"]').setInputFiles({
        name: "avatar.png",
        mimeType: "image/png",
        buffer: Buffer.from("profile-avatar-preview"),
      })
      await expect(page.getByAltText("Profile avatar preview")).toBeVisible()

      const displayName = page.getByLabel("Display name")
      await displayName.fill("Taylor Updated")
      await page.getByRole("button", { name: "Save changes" }).click()
      await expect(page.getByRole("status")).toContainText(
        "Profile changes saved",
      )
      await page.reload()
      await expect(page.getByLabel("Display name")).toHaveValue(
        "Taylor Updated",
      )
      await expect(page.getByAltText("Profile avatar preview")).toBeVisible()

      await expect(
        page.getByRole("button", { name: "Export my data" }),
      ).toBeVisible()
      await expect(
        page.getByRole("button", { name: "Delete local profile" }),
      ).toHaveCount(0)

      const accessibility = await new AxeBuilder({ page }).analyze()
      expect(accessibility.violations).toEqual([])

      await page.setViewportSize({ width: 390, height: 844 })
      await expect(page.getByLabel("Preferred language")).toBeVisible()
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth > window.innerWidth,
        ),
      ).toBe(false)
    })
  })
