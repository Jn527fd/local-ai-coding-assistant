import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { sendChatStream } from "../api.js";
import { buildDefaultConversationSettings } from "../chatState.js";
import { useChatSender } from "./useChatSender.js";

vi.mock("../api.js", () => ({
  sendChatStream: vi.fn(),
}));

function renderChatSender({ activeChat, apiKey = "test-key" } = {}) {
  let chats = activeChat ? [activeChat] : [];
  const setCurrentSection = vi.fn();
  const setChats = vi.fn((updater) => {
    chats = typeof updater === "function" ? updater(chats) : updater;
  });
  const hook = renderHook(() =>
    useChatSender({
      activeChat,
      apiKey,
      defaultConversationSettings: buildDefaultConversationSettings(),
      modelStatus: { active_model: "llama" },
      setChats,
      setCurrentSection,
    }),
  );
  return { ...hook, getChats: () => chats, setCurrentSection, setChats };
}

describe("useChatSender", () => {
  beforeEach(() => {
    sendChatStream.mockReset();
  });

  it("streams into an optimistic assistant message and stores metadata", async () => {
    const activeChat = {
      id: "chat-a",
      title: "Untitled",
      settings: {},
      messages: [],
    };
    sendChatStream.mockImplementationOnce(async (...args) => {
      const options = args.at(-1);
      options.onToken("Hello");
      options.onToken(" there");
      return {
        answer: "Hello there",
        model: "llama",
        ragUsed: true,
        rerankingUsed: true,
        compressionUsed: true,
        sources: [{ documentName: "notes.txt" }],
      };
    });
    const { result, getChats } = renderChatSender({ activeChat });

    let sent;
    await act(async () => {
      sent = await result.current.handleSendMessage("Explain this");
    });

    expect(sent).toBe(true);
    expect(result.current.sendingChatId).toBe("");
    const messages = getChats()[0].messages;
    expect(messages).toHaveLength(2);
    expect(messages[0]).toMatchObject({ role: "user", content: "Explain this" });
    expect(messages[1]).toMatchObject({
      role: "assistant",
      content: "Hello there",
      streaming: false,
      model: "llama",
      ragUsed: true,
      rerankingUsed: true,
      compressionUsed: true,
    });
  });

  it("includes attached documents in the user message and RAG request options", async () => {
    const activeChat = {
      id: "chat-a",
      title: "Untitled",
      settings: {},
      messages: [],
    };
    sendChatStream.mockResolvedValueOnce({
      answer: "The certificate says hello.",
      model: "llama",
      ragUsed: true,
      sources: [{ documentName: "certificates.pdf" }],
    });
    const { result, getChats } = renderChatSender({ activeChat });

    let sent;
    await act(async () => {
      sent = await result.current.handleSendMessage(
        "Use the certificate",
        [],
        [
          {
            documentId: "doc-1",
            originalFilename: "certificates.pdf",
            status: "processed",
          },
        ],
      );
    });

    expect(sent).toBe(true);
    expect(sendChatStream).toHaveBeenCalledWith(
      "test-key",
      "Use the certificate",
      [],
      expect.any(Object),
      "chat-a",
      {
        enabled: true,
        documentIds: ["doc-1"],
        includeSources: true,
      },
      [],
      expect.any(Object),
    );
    expect(getChats()[0].messages[0]).toMatchObject({
      role: "user",
      content: "Use the certificate",
      documentAttachments: [
        {
          documentId: "doc-1",
          originalFilename: "certificates.pdf",
          status: "processed",
        },
      ],
    });
  });

  it("removes the optimistic assistant message when streaming fails", async () => {
    const activeChat = {
      id: "chat-a",
      title: "Untitled",
      settings: {},
      messages: [],
    };
    sendChatStream.mockRejectedValueOnce(new Error("backend offline"));
    const { result, getChats } = renderChatSender({ activeChat });

    let sent;
    await act(async () => {
      sent = await result.current.handleSendMessage("Hello");
    });

    expect(sent).toBe(false);
    expect(result.current.chatError).toBe("backend offline");
    expect(getChats()[0].messages).toEqual([
      expect.objectContaining({ role: "user", content: "Hello" }),
    ]);
  });

  it("requires an API key before sending", async () => {
    const { result } = renderChatSender({
      apiKey: "",
      activeChat: { id: "chat-a", settings: {}, messages: [] },
    });

    let sent;
    await act(async () => {
      sent = await result.current.handleSendMessage("Hello");
    });

    expect(sent).toBe(false);
    expect(result.current.chatError).toMatch(/api key/i);
    expect(sendChatStream).not.toHaveBeenCalled();
  });
});
