import { expect, test } from "@playwright/test";

async function signIn(page) {
  await page.addInitScript(() => {
    window.localStorage.setItem("local-ai-coding-assistant.api-key", "test-key");
  });
  await page.goto("/");
  await page.getByLabel("Username").fill("test-user");
  await page.getByLabel("Password").fill("test-password-123");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Bring local intelligence to your codebase.")).toBeVisible();
}

async function attachScreenshot(page, testInfo, name) {
  const screenshot = await page.screenshot({ fullPage: true });
  expect(screenshot.byteLength).toBeGreaterThan(1_000);
  await testInfo.attach(name, {
    body: screenshot,
    contentType: "image/png",
  });
}

test.describe("visual regression artifacts", () => {
  test("captures no repo state", async ({ page }, testInfo) => {
    await signIn(page);
    await attachScreenshot(page, testInfo, "no-repo-state");
  });

  test("captures active conversation", async ({ page }, testInfo) => {
    await signIn(page);
    await page.getByRole("button", { name: /new/i }).click();
    await page.getByLabel("Ask about your codebase").fill("Explain the runtime.");
    await page.keyboard.press(process.platform === "darwin" ? "Meta+Enter" : "Control+Enter");
    await expect(page.getByText(/Fake Ollama response/i)).toBeVisible();
    await attachScreenshot(page, testInfo, "active-conversation");
  });

  test("captures command palette", async ({ page }, testInfo) => {
    await signIn(page);
    await page.keyboard.press(process.platform === "darwin" ? "Meta+K" : "Control+K");
    await expect(page.getByRole("dialog", { name: /command palette/i })).toBeVisible();
    await attachScreenshot(page, testInfo, "command-palette");
  });

  test("captures context drawer", async ({ page }, testInfo) => {
    await signIn(page);
    await page.getByRole("button", { name: /open context drawer/i }).click();
    await expect(page.getByRole("complementary", { name: /workspace context/i })).toBeVisible();
    await attachScreenshot(page, testInfo, "context-drawer");
  });

  test("captures models page", async ({ page }, testInfo) => {
    await signIn(page);
    await page.getByRole("button", { name: /qwen3:4b/i }).click();
    await expect(page.getByRole("combobox", { name: /model catalog/i })).toBeVisible();
    await attachScreenshot(page, testInfo, "models-page");
  });

  test("captures mobile layout", async ({ page, isMobile }, testInfo) => {
    test.skip(!isMobile, "mobile project only");
    await signIn(page);
    await expect(page.getByRole("navigation", { name: /mobile navigation/i })).toBeVisible();
    await attachScreenshot(page, testInfo, "mobile-layout");
  });
});
