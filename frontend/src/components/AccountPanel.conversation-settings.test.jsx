import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AccountPanel from "./AccountPanel.jsx";

const capabilities = {
  llmModels: [
    { id: "qwen3:4b", label: "qwen3:4b", available: true },
    { id: "llama3.2:3b", label: "llama3.2:3b", available: true },
  ],
  embedderModels: [
    { id: "nomic-embed-text:latest", label: "nomic-embed-text:latest", available: true },
  ],
  rerankerModels: [],
  visionModels: [],
  ocrEngines: [{ id: "none", label: "None", available: true }],
  pdfParsers: [{ id: "pymupdf", label: "PyMuPDF", available: true }],
  chunkers: [{ id: "recursive", label: "Recursive", available: true }],
  vectorDatabases: [{ id: "chroma", label: "Chroma", available: true }],
  ragPipelines: [{ id: "basic", label: "Basic", available: true }],
  contextCompressors: [{ id: "none", label: "None", available: true }],
};

function renderAccountPanel(props = {}) {
  return render(
    <AccountPanel
      activeConversationSettings={{
        llmModel: "qwen3:4b",
        embedderModel: "nomic-embed-text:latest",
        ocrEngine: "none",
        pdfParser: "pymupdf",
        chunker: "recursive",
        vectorDatabase: "chroma",
        ragPipeline: "basic",
        reranker: "none",
        contextCompressor: "none",
        visionModel: "none",
      }}
      activeConversationTitle="Chat A"
      apiKey="test-key"
      capabilities={capabilities}
      capabilitiesStatus={{ status: "ready", message: "" }}
      isOpen
      onApiKeyChange={vi.fn()}
      onClose={vi.fn()}
      onConversationSettingsChange={vi.fn()}
      onLogout={vi.fn()}
      onModelStatus={vi.fn()}
      onRefreshCapabilities={vi.fn()}
      username="test-user"
      {...props}
    />,
  );
}

describe("AccountPanel conversation settings", () => {
  it("shows the active chat settings and emits setting patches", async () => {
    const user = userEvent.setup();
    const onConversationSettingsChange = vi.fn();
    const { rerender } = renderAccountPanel({
      onConversationSettingsChange,
    });

    const llmSelect = screen.getByRole("combobox", { name: /llm model/i });
    expect(llmSelect).toHaveValue("qwen3:4b");

    await user.selectOptions(llmSelect, "llama3.2:3b");
    expect(onConversationSettingsChange).toHaveBeenCalledWith({
      llmModel: "llama3.2:3b",
    });

    rerender(
      <AccountPanel
        activeConversationSettings={{
          llmModel: "llama3.2:3b",
          embedderModel: "nomic-embed-text:latest",
          ocrEngine: "none",
          pdfParser: "pymupdf",
          chunker: "recursive",
          vectorDatabase: "chroma",
          ragPipeline: "basic",
          reranker: "none",
          contextCompressor: "none",
          visionModel: "none",
        }}
        activeConversationTitle="Chat B"
        apiKey="test-key"
        capabilities={capabilities}
        capabilitiesStatus={{ status: "ready", message: "" }}
        isOpen
        onApiKeyChange={vi.fn()}
        onClose={vi.fn()}
        onConversationSettingsChange={onConversationSettingsChange}
        onLogout={vi.fn()}
        onModelStatus={vi.fn()}
        onRefreshCapabilities={vi.fn()}
        username="test-user"
      />,
    );

    expect(screen.getByRole("combobox", { name: /llm model/i })).toHaveValue(
      "llama3.2:3b",
    );
    expect(screen.getByText(/Chat B/)).toBeInTheDocument();
  });
});
