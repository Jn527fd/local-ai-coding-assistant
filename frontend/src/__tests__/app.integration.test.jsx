import React from "react";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

    const palette = await screen.findByRole("dialog", { name: /command palette/i });
    expect(palette).toBeInTheDocument();
    expect(within(palette).getByRole("button", { name: /new chat/i })).toBeInTheDocument();
  });

  it("sends a chat message and shows a streaming state before the answer", async () => {
    server.use(
      http.post(`${API_BASE_URL}/chat`, async ({ request }) => {
        const body = await request.json();
        await delay(220);
        return HttpResponse.json({
          model: "qwen3:4b",
          answer: `Fake streaming answer: ${body.message}`,
          ragUsed: true,
          rerankingUsed: true,
          rerankerModel: "bge-reranker:latest",
          ragWarnings: ["Document context skipped one stale index."],
          rerankWarnings: ["Reranker skipped one low-confidence score."],
          compressionUsed: true,
          compressorMode: "token",
          compressionWarnings: ["Token compression trimmed 2 older history messages."],
          compressionStats: {
            originalCharEstimate: 18000,
            compressedCharEstimate: 9000,
            originalTokenEstimate: 4500,
            compressedTokenEstimate: 2250,
            messagesTrimmed: 2,
            contextTrimmed: 0,
            summaryGenerated: false,
          },
          sources: [
            {
              sourceNumber: 1,
              documentId: "doc-1",
              documentName: "notes.txt",
              chunkId: "chunk-1",
              chunkIndex: 0,
              score: 0.91,
              vectorScore: 0.51,
              rerankScore: 0.91,
              finalRank: 1,
              textPreview: "The FastAPI app is created in backend/app/main.py.",
            },
          ],
        });
      }),
    );
    const user = userEvent.setup();
    await renderAuthenticatedApp();

    await user.click(screen.getByRole("button", { name: /new chat/i }));
    await user.type(
      screen.getByRole("textbox", { name: /message assistant/i }),
      "Where is the FastAPI app created?",
    );
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(await screen.findByLabelText(/assistant is responding/i)).toBeInTheDocument();
    expect(await screen.findByText(/Fake streaming answer/)).toBeInTheDocument();
    expect(screen.getByText(/used reranked document context/i)).toBeInTheDocument();
    expect(screen.getByText(/context compressed/i)).toBeInTheDocument();
    expect(screen.getByText(/stale index/i)).toBeInTheDocument();
    expect(screen.getByText(/low-confidence score/i)).toBeInTheDocument();
    expect(screen.getByText(/trimmed 2 older history/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open source notes\.txt/i })).toHaveTextContent(/R 0\.91/i);
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
