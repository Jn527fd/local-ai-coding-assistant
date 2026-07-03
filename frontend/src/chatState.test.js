import { describe, expect, it } from "vitest";

import {
  buildDefaultConversationSettings,
  chatStorageKey,
  conversationPersistenceKey,
  createChat,
  loadChats,
  loadConversationPersistenceMode,
  normalizeConversationSettings,
  PERSISTENCE_MODE_BACKEND,
  PERSISTENCE_MODE_LOCAL,
  saveConversationPersistenceMode,
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
  it("builds defaults from the first alphabetical LLM and discovered capabilities", () => {
    const defaults = buildDefaultConversationSettings({
      capabilities,
    });

    expect(defaults).toMatchObject({
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
    });
  });

  it("migrates existing localStorage chats to include settings", () => {
    const defaults = buildDefaultConversationSettings({
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
      capabilities,
    });
    const firstChat = createChat(defaults);
    const secondChat = createChat(defaults);

    firstChat.settings.llmModel = "qwen3:4b";

    expect(secondChat.settings.llmModel).toBe("llama3.2:3b");
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

  it("keeps browser-local persistence as the default", () => {
    expect(loadConversationPersistenceMode("test-user")).toBe(
      PERSISTENCE_MODE_LOCAL,
    );
  });

  it("stores an explicit backend persistence opt-in", () => {
    saveConversationPersistenceMode("test-user", PERSISTENCE_MODE_BACKEND);

    expect(window.localStorage.getItem(conversationPersistenceKey("test-user"))).toBe(
      PERSISTENCE_MODE_BACKEND,
    );
    expect(loadConversationPersistenceMode("test-user")).toBe(
      PERSISTENCE_MODE_BACKEND,
    );
  });
});
