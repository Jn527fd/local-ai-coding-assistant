import { describe, expect, it } from "vitest";

import {
  buildDefaultConversationSettings,
  chatStorageKey,
  createChat,
  loadChats,
  normalizeConversationSettings,
} from "./chatState.js";

const capabilities = {
  llmModels: [
    { id: "llama3.2:3b", label: "llama3.2:3b", available: true },
    { id: "qwen3:4b", label: "qwen3:4b", available: true },
  ],
  embedderModels: [
    { id: "nomic-embed-text:latest", label: "nomic", available: true },
  ],
  pdfParsers: [
    { id: "pdfplumber", label: "pdfplumber", available: true },
    { id: "pymupdf", label: "PyMuPDF", available: true },
  ],
};

describe("conversation settings state", () => {
  it("builds defaults from active model and discovered capabilities", () => {
    const defaults = buildDefaultConversationSettings({
      activeModel: "qwen3:4b",
      capabilities,
    });

    expect(defaults).toMatchObject({
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
    });
  });

  it("migrates existing localStorage chats to include settings", () => {
    const defaults = buildDefaultConversationSettings({
      activeModel: "qwen3:4b",
      capabilities,
    });
    window.localStorage.setItem(
      chatStorageKey("test-user"),
      JSON.stringify([
        {
          id: "chat-1",
          title: "Old chat",
          messages: [{ role: "user", content: "Hello" }],
          updatedAt: "2026-06-27T12:00:00.000Z",
        },
      ]),
    );

    const chats = loadChats("test-user", defaults);

    expect(chats).toHaveLength(1);
    expect(chats[0].settings).toEqual(defaults);
  });

  it("fills partial or corrupted settings safely", () => {
    const defaults = buildDefaultConversationSettings({
      activeModel: "qwen3:4b",
      capabilities,
    });

    expect(normalizeConversationSettings("bad-settings", defaults)).toEqual(
      defaults,
    );
    expect(
      normalizeConversationSettings({ llmModel: "custom:latest" }, defaults),
    ).toEqual({
      ...defaults,
      llmModel: "custom:latest",
    });
  });

  it("gives new chats independent settings copies", () => {
    const defaults = buildDefaultConversationSettings({
      activeModel: "qwen3:4b",
      capabilities,
    });
    const firstChat = createChat(defaults);
    const secondChat = createChat(defaults);

    firstChat.settings.llmModel = "llama3.2:3b";

    expect(secondChat.settings.llmModel).toBe("qwen3:4b");
  });

  it("preserves distinct per-chat settings after reload", () => {
    window.localStorage.setItem(
      chatStorageKey("test-user"),
      JSON.stringify([
        {
          id: "chat-a",
          title: "A",
          messages: [],
          updatedAt: "2026-06-27T12:00:00.000Z",
          settings: { llmModel: "qwen3:4b", chunker: "recursive" },
        },
        {
          id: "chat-b",
          title: "B",
          messages: [],
          updatedAt: "2026-06-27T12:01:00.000Z",
          settings: { llmModel: "llama3.2:3b", chunker: "fixed" },
        },
      ]),
    );

    const chats = loadChats(
      "test-user",
      buildDefaultConversationSettings({
        activeModel: "qwen3:4b",
        capabilities,
      }),
    );

    expect(chats.find((chat) => chat.id === "chat-a").settings.llmModel).toBe(
      "qwen3:4b",
    );
    expect(chats.find((chat) => chat.id === "chat-b").settings.llmModel).toBe(
      "llama3.2:3b",
    );
    expect(chats.find((chat) => chat.id === "chat-b").settings.chunker).toBe(
      "fixed",
    );
  });
});
