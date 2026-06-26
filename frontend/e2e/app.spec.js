import { expect, test } from "@playwright/test";

async function signIn(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("local-ai-coding-assistant.api-key", "test-key");
  });
  await page.goto("/");
  await page.getByLabel("Username").fill("test-user");
  await page.getByLabel("Password").fill("test-password-123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(
    page.getByText("Bring local intelligence to your codebase."),
  ).toBeVisible();
}

test.describe("local AI coding assistant", () => {
  test("app loads and signs in with local credentials", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByText("Local AI Coding Assistant")).toBeVisible();
    await expect(page.getByText("Private coding intelligence for your machine.")).toBeVisible();

    await signIn(page);
    await expect(page.getByText("Local Intelligence Command Center")).toBeVisible();
  });

  test("no-repo onboarding flow renders", async ({ page }) => {
    await signIn(page);

    await expect(page.getByRole("button", { name: /index repository/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /open model settings/i })).toBeVisible();
    await expect(page.getByText("Drop a local folder here")).toBeVisible();
    await expect(page.getByText("Source-grounded answers")).toBeVisible();
  });

  test("command palette keyboard navigation works", async ({ page }) => {
    await signIn(page);

    await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
    await expect(page.getByRole("dialog", { name: /command palette/i })).toBeVisible();
    await page.getByPlaceholder("Search, ask, or run a command...").fill("runtime");

    await expect(page.getByRole("button", { name: /view runtime health/i })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog", { name: /command palette/i })).toBeHidden();
  });

  test("chat send flow works with fake Ollama", async ({ page }) => {
    await signIn(page);

    await page.getByRole("button", { name: /new/i }).click();
    await page.getByLabel("Ask about your codebase").fill("Where is FastAPI created?");
    await page.keyboard.press(process.platform === "darwin" ? "Meta+Enter" : "Control+Enter");

    await expect(page.getByLabel("Assistant is responding")).toBeVisible();
    await expect(page.getByText(/Fake Ollama response/i)).toBeVisible();
  });

  test("model switching works with mocked Ollama models", async ({ page }) => {
    await signIn(page);
    page.once("dialog", (dialog) => dialog.accept());

    await page.getByRole("button", { name: /qwen3:4b/i }).click();
    await page.getByRole("combobox", { name: /model catalog/i }).selectOption("llama3.2:3b");
    await page.getByRole("button", { name: /use installed model/i }).click();

    await expect(page.locator(".model-summary strong")).toHaveText("llama3.2:3b");
  });

  test("context drawer opens from Context button and citation click", async ({ page }) => {
    await signIn(page);

    await page.getByRole("button", { name: /open context drawer/i }).click();
    await expect(page.getByRole("complementary", { name: /workspace context/i })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("complementary", { name: /workspace context/i })).toBeHidden();

    await page.getByRole("button", { name: /new/i }).click();
    await page.getByLabel("Ask about your codebase").fill("Show me sources");
    await page.keyboard.press(process.platform === "darwin" ? "Meta+Enter" : "Control+Enter");
    await page.getByRole("button", { name: /open source backend\/app\/main.py/i }).click();
    await expect(page.getByRole("complementary", { name: /workspace context/i })).toBeVisible();
  });

  test("runtime disconnected state is handled", async ({ page }) => {
    await page.route("**/health", (route) =>
      route.fulfill({
        status: 503,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Backend unavailable" }),
      }),
    );
    await page.route("**/models/status", (route) =>
      route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          active_model: "qwen3:4b",
          supported_models: [],
          installed_models: [],
          ollama_connected: false,
          switching: false,
          target_model: null,
          phase: "idle",
          progress: null,
          message: "Ready",
          error: "Ollama offline",
          warning: null,
        }),
      }),
    );

    await signIn(page);

    await expect(page.getByText("Local runtime needs attention")).toBeVisible();
  });

  test("responsive mobile layout renders", async ({ page, isMobile }) => {
    test.skip(!isMobile, "mobile project only");

    await signIn(page);

    await expect(page.getByRole("navigation", { name: /mobile navigation/i })).toBeVisible();
    await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Context" })).toBeVisible();
  });
});
