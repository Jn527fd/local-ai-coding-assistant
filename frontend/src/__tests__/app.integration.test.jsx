import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { delay, http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import App from "../App.jsx";
import { API_BASE_URL, runtimeOfflineHandlers } from "../test/msw/handlers.js";
import { server } from "../test/msw/server.js";

function seedApiKey() {
  window.localStorage.setItem("local-ai-coding-assistant.api-key", "test-key");
}

async function renderAuthenticatedApp() {
  seedApiKey();
  render(<App />);
  await screen.findByText("Where should we begin?");
}

describe("main app integration", () => {
  it("opens with no repository indexed and a clear onboarding action", async () => {
    await renderAuthenticatedApp();

    expect(screen.queryByText("No repository indexed")).not.toBeInTheDocument();
    expect(
      screen.getByText(/conversation stays on this machine/i),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /index repository/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /drop a local folder here/i })).not.toBeInTheDocument();
  });

  it("opens and closes the recents drawer from the rail", async () => {
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /menu and recents/i }));

    expect(
      await screen.findByRole("complementary", { name: /recent conversations drawer/i }),
    ).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search chats/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /menu and recents/i }));

    expect(
      screen.queryByRole("complementary", { name: /recent conversations drawer/i }),
    ).not.toBeInTheDocument();
  });

  it("opens the command palette with Ctrl+K", async () => {
    await renderAuthenticatedApp();

    fireEvent.keyDown(window, { key: "k", ctrlKey: true });

    expect(
      await screen.findByRole("dialog", { name: /command palette/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /ask codebase/i })).toBeInTheDocument();
  });

  it("sends a chat message and shows a streaming state before the answer", async () => {
    server.use(
      http.post(`${API_BASE_URL}/chat`, async ({ request }) => {
        const body = await request.json();
        await delay(220);
        return HttpResponse.json({
          model: "qwen3:4b",
          answer: `Fake streaming answer: ${body.message}`,
          sources: ["backend/app/main.py"],
        });
      }),
    );
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /new chat/i }));
    await user.type(
      screen.getByRole("textbox", { name: /ask about your codebase/i }),
      "Where is the FastAPI app created?",
    );
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(await screen.findByLabelText(/assistant is responding/i)).toBeInTheDocument();
    expect(await screen.findByText(/Fake streaming answer/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open source backend\/app\/main.py/i })).toBeInTheDocument();
  });

  it("shows mocked Ollama models from the model selector", async () => {
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /^Settings$/i }));

    expect(
      await screen.findByRole("complementary", { name: /account and api settings/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /model catalog/i })).toHaveTextContent(
      "llama3.2:3b",
    );
  });

  it("shows a clear offline runtime state", async () => {
    const user = userEvent.setup();
    server.use(...runtimeOfflineHandlers);
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /^Settings$/i }));

    await waitFor(() => {
      expect(screen.getAllByText("Ollama offline").length).toBeGreaterThan(0);
    });
  });

  it("keeps source citation actions lightweight without opening an extra panel", async () => {
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /new chat/i }));
    await user.type(screen.getByRole("textbox"), "Show citations");
    await user.keyboard("{Control>}{Enter}{/Control}");
    await user.click(
      await screen.findByRole("button", {
        name: /open source backend\/app\/main.py/i,
      }),
    );

    expect(screen.queryByRole("complementary", { name: /workspace context/i })).not.toBeInTheDocument();
    expect(await screen.findByText("Source: backend/app/main.py")).toBeInTheDocument();
  });
});
