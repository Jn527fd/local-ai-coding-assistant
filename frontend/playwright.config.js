import { defineConfig, devices } from "@playwright/test";

const isCi = Boolean(process.env.CI);

export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  expect: {
    timeout: 8_000,
  },
  fullyParallel: true,
  forbidOnly: isCi,
  retries: isCi ? 1 : 0,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "python tests/fakes/fake_ollama.py",
      cwd: "..",
      env: {
        ...process.env,
        FAKE_OLLAMA_PORT: "11435",
        FAKE_OLLAMA_SCENARIO: "success",
      },
      port: 11435,
      reuseExistingServer: !isCi,
      timeout: 20_000,
    },
    {
      command: "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: "../backend",
      env: {
        ...process.env,
        API_KEY: "test-key",
        APP_ENVIRONMENT: "test",
        CORS_ORIGINS: "http://127.0.0.1:5173,http://localhost:5173",
        CREDENTIALS_FILE: "../tests/fixtures/credentials.e2e.json",
        LOCAL_SETTINGS_FILE: "../tmp/e2e-app-settings.json",
        DATA_DIRECTORY: "../tmp/e2e-data",
        DEFAULT_MODEL: "qwen3:4b",
        OLLAMA_BASE_URL: "http://127.0.0.1:11435",
        OLLAMA_TIMEOUT_SECONDS: "3",
      },
      port: 8000,
      reuseExistingServer: !isCi,
      timeout: 20_000,
    },
    {
      command: "node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173",
      env: {
        ...process.env,
        VITE_API_BASE_URL: "http://127.0.0.1:8000",
      },
      port: 5173,
      reuseExistingServer: !isCi,
      timeout: 20_000,
    },
  ],
  projects: [
    {
      name: "desktop",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } },
    },
    {
      name: "mobile",
      use: { ...devices["Pixel 5"] },
    },
  ],
});
