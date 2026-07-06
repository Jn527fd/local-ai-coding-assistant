import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
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

    const palette = await screen.findByRole("dialog", { name: /command palette/i });
    expect(palette).toBeInTheDocument();
    expect(within(palette).getByRole("button", { name: /new chat/i })).toBeInTheDocument();
  });

  it("sends a chat message and shows a streaming state before the answer", async () => {
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /new chat/i }));
    await user.type(
      screen.getByRole("textbox", { name: /message assistant/i }),
      "Where is the FastAPI app created?",
    );
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(await screen.findByText("Streaming locally")).toBeInTheDocument();
    expect(
      await screen.findByText(/Fake streaming answer/, {}, { timeout: 6000 }),
    ).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText("Streaming locally")).not.toBeInTheDocument();
    });
    expect(screen.queryByText("Preparing response")).not.toBeInTheDocument();
    expect(screen.getByText(/used reranked document context/i)).toBeInTheDocument();
    expect(screen.getByText(/context compressed/i)).toBeInTheDocument();
    expect(screen.getByText(/stale index/i)).toBeInTheDocument();
    expect(screen.getByText(/low-confidence score/i)).toBeInTheDocument();
    expect(screen.getByText(/trimmed 2 older history/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open source notes\.txt/i })).toHaveTextContent(/R 0\.91/i);
  });

  it("shows mocked Ollama models from the per-chat model selector", async () => {
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /^Settings$/i }));

    expect(
      await screen.findByRole("complementary", { name: /account and api settings/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: /llm model/i })).toHaveTextContent(
      "llama3.2:3b",
    );
  });

  it("opens diagnostics from the rail", async () => {
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /^diagnostics$/i }));

    expect(await screen.findByRole("region", { name: /diagnostics/i })).toBeInTheDocument();
    expect(screen.getByText("Runtime overview")).toBeInTheDocument();
    expect(screen.getByText("qwen3:4b")).toBeInTheDocument();
    expect(screen.getByText("document_index: 1")).toBeInTheDocument();
  });

  it("keeps browser storage by default and migrates when explicitly requested", async () => {
    let importBody = null;
    server.use(
      http.post(`${API_BASE_URL}/conversations/import`, async ({ request }) => {
        importBody = await request.json();
        return HttpResponse.json({
          imported: importBody.conversations.length,
          conversations: importBody.conversations,
        });
      }),
    );
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    expect(
      window.localStorage.getItem(
        "local-ai-coding-assistant.conversation-persistence.test-user",
      ),
    ).toBeNull();

    await user.click(screen.getByRole("button", { name: /^Settings$/i }));
    expect(screen.getByText(/browser localstorage/i)).toBeInTheDocument();

    await user.click(
      screen.getByRole("button", { name: /migrate to backend storage/i }),
    );

    await waitFor(() => {
      expect(importBody?.replace).toBe(true);
    });
    expect(importBody.conversations.length).toBeGreaterThan(0);
    expect(
      window.localStorage.getItem(
        "local-ai-coding-assistant.conversation-persistence.test-user",
      ),
    ).toBe("backend");
    expect(
      await screen.findByText(/browser chats migrated to backend storage/i),
    ).toBeInTheDocument();
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
