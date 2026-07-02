import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AccountPanel from "./AccountPanel.jsx";

const capabilities = {
  llmModels: [
    {
      id: "qwen3:4b",
      label: "qwen3:4b",
      available: true,
      implementationStatus: "implemented",
      execution: {
        description: "Model can be used through the local Ollama provider.",
      },
    },
    {
      id: "llama3.2:3b",
      label: "llama3.2:3b",
      available: true,
      implementationStatus: "implemented",
      execution: {
        description: "Model can be used through the local Ollama provider.",
      },
    },
  ],
  embedderModels: [
    {
      id: "nomic-embed-text:latest",
      label: "nomic-embed-text:latest",
      available: true,
      implementationStatus: "implemented",
      execution: {
        description: "Model can be used through the local Ollama provider.",
      },
    },
  ],
  rerankerModels: [],
  visionModels: [],
  ocrEngines: [
    {
      id: "none",
      label: "None",
      available: true,
      implementationStatus: "implemented",
      execution: { description: "Disables OCR for document processing." },
    },
  ],
  pdfParsers: [
    {
      id: "pymupdf",
      label: "PyMuPDF",
      available: true,
      implementationStatus: "implemented",
      execution: { description: "Extracts selectable PDF text with PyMuPDF." },
    },
  ],
  chunkers: [
    {
      id: "recursive",
      label: "Recursive",
      available: true,
      implementationStatus: "implemented",
      execution: {
        description: "Splits documents on paragraph-aware recursive boundaries.",
      },
    },
  ],
  vectorDatabases: [
    {
      id: "chroma",
      label: "Chroma",
      available: true,
      implementationStatus: "fallback",
      execution: {
        description: "Selection is recorded; vectors are stored in the local JSON index.",
      },
    },
  ],
  ragPipelines: [
    {
      id: "basic",
      label: "Basic",
      available: true,
      implementationStatus: "implemented",
      execution: {
        description: "Uses local vector retrieval when document RAG is enabled.",
      },
    },
  ],
  contextCompressors: [
    {
      id: "none",
      label: "None",
      available: true,
      implementationStatus: "implemented",
      execution: { description: "Leaves chat history and retrieved context unchanged." },
    },
  ],
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

  it("lets users verify the active chat settings", async () => {
    const user = userEvent.setup();
    const onConversationSettingsVerified = vi.fn();
    const onConversationSettingsChange = vi.fn();
    renderAccountPanel({
      onConversationSettingsChange,
      onConversationSettingsVerified,
    });

    await user.click(
      screen.getByRole("button", { name: /verify chat settings/i }),
    );

    expect(onConversationSettingsVerified).toHaveBeenCalledWith("Chat A");
    expect(screen.getByRole("status")).toHaveTextContent(
      /settings verified for "chat a"/i,
    );

    await user.selectOptions(
      screen.getByRole("combobox", { name: /llm model/i }),
      "llama3.2:3b",
    );

    expect(onConversationSettingsChange).toHaveBeenCalledWith({
      llmModel: "llama3.2:3b",
    });
    expect(
      screen.queryByText(/settings verified for "chat a"/i),
    ).not.toBeInTheDocument();
  });

  it("shows execution metadata for selected capabilities", () => {
    renderAccountPanel();

    expect(
      screen.getAllByText(/implemented: model can be used/i).length,
    ).toBeGreaterThan(0);
    expect(screen.getByText(/fallback: selection is recorded/i)).toBeInTheDocument();
    expect(
      screen.getByText(/implemented: extracts selectable pdf text/i),
    ).toBeInTheDocument();
  });
});
