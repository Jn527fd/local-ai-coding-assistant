import { useCallback, useState } from "react";

import { sendChatStream } from "../api.js";
import { normalizeConversationSettings, titleFromMessage } from "../chatState.js";

export function useChatSender({
  activeChat,
  apiKey,
  defaultConversationSettings,
  modelStatus,
  setChats,
  setCurrentSection,
}) {
  const [sendingChatId, setSendingChatId] = useState("");
  const [chatError, setChatError] = useState("");

  const resetChatSender = useCallback(() => {
    setSendingChatId("");
    setChatError("");
  }, []);

  const handleSendMessage = useCallback(
    async (message, imageAttachments = []) => {
      if (!apiKey) {
        setChatError("Save and verify your API key from Settings before chatting.");
        return false;
      }

      if (!activeChat) {
        setChatError("Create a chat before sending a message.");
        return false;
      }

      const chatId = activeChat.id;
      const history = activeChat.messages
        .slice(-30)
        .map(({ role, content }) => ({ role, content }));
      const userMessage = {
        role: "user",
        content: message,
        imageAttachments: imageAttachments.map(({ data, ...metadata }) => metadata),
        createdAt: new Date().toISOString(),
      };
      const assistantMessageId =
        globalThis.crypto?.randomUUID?.() || `assistant-${Date.now()}`;

      setChatError("");
      setSendingChatId(chatId);
      setCurrentSection("ask");
      setChats((current) =>
        current.map((chat) =>
          chat.id === chatId
            ? {
                ...chat,
                title:
                  chat.messages.length === 0
                    ? titleFromMessage(message)
                    : chat.title,
                messages: [
                  ...chat.messages,
                  userMessage,
                  {
                    id: assistantMessageId,
                    role: "assistant",
                    content: "",
                    streaming: true,
                    createdAt: new Date().toISOString(),
                  },
                ],
                updatedAt: new Date().toISOString(),
              }
            : chat,
        ),
      );

      try {
        const generationStartedAt =
          typeof globalThis.performance?.now === "function"
            ? globalThis.performance.now()
            : Date.now();
        const conversationSettings = normalizeConversationSettings(
          activeChat.settings,
          defaultConversationSettings,
        );
        let streamedContent = "";
        const result = await sendChatStream(
          apiKey,
          message,
          history,
          conversationSettings,
          chatId,
          null,
          imageAttachments.map(({ name, mimeType, data }) => ({
            name,
            mimeType,
            data,
          })),
          {
            onToken: (token) => {
              streamedContent += token;
              setChats((current) =>
                current.map((chat) =>
                  chat.id === chatId
                    ? {
                        ...chat,
                        messages: chat.messages.map((item) =>
                          item.id === assistantMessageId
                            ? { ...item, content: streamedContent }
                            : item,
                        ),
                      }
                    : chat,
                ),
              );
            },
          },
        );
        const generationEndedAt =
          typeof globalThis.performance?.now === "function"
            ? globalThis.performance.now()
            : Date.now();
        const sources = Array.isArray(result.sources) ? result.sources : [];
        const ragWarnings = Array.isArray(result.ragWarnings)
          ? result.ragWarnings
          : [];
        const rerankWarnings = Array.isArray(result.rerankWarnings)
          ? result.rerankWarnings
          : [];
        const compressionWarnings = Array.isArray(result.compressionWarnings)
          ? result.compressionWarnings
          : [];
        setChats((current) =>
          current.map((chat) =>
            chat.id === chatId
              ? {
                  ...chat,
                  messages: chat.messages.map((item) =>
                    item.id === assistantMessageId
                      ? {
                          ...item,
                          content: result.answer || streamedContent,
                          streaming: false,
                          generationTimeMs: Math.max(
                            0,
                            Math.round(generationEndedAt - generationStartedAt),
                          ),
                          model:
                            result.model ||
                            result.model_used ||
                            modelStatus?.active_model ||
                            "Local model",
                          ragUsed: Boolean(result.ragUsed),
                          ragWarnings,
                          rerankingUsed: Boolean(result.rerankingUsed),
                          rerankerModel: result.rerankerModel || "",
                          rerankWarnings,
                          compressionUsed: Boolean(result.compressionUsed),
                          compressorMode: result.compressorMode || "none",
                          compressionWarnings,
                          compressionStats: result.compressionStats || null,
                          visionUsed: Boolean(result.visionUsed),
                          visionModel: result.visionModel || "",
                          visionWarnings: Array.isArray(result.visionWarnings)
                            ? result.visionWarnings
                            : [],
                          sources,
                        }
                      : item,
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : chat,
          ),
        );
        return true;
      } catch (requestError) {
        setChatError(requestError.message);
        setChats((current) =>
          current.map((chat) =>
            chat.id === chatId
              ? {
                  ...chat,
                  messages: chat.messages.filter(
                    (item) => item.id !== assistantMessageId,
                  ),
                  updatedAt: new Date().toISOString(),
                }
              : chat,
          ),
        );
        return false;
      } finally {
        setSendingChatId("");
      }
    },
    [
      activeChat,
      apiKey,
      defaultConversationSettings,
      modelStatus,
      setChats,
      setCurrentSection,
    ],
  );

  return {
    chatError,
    handleSendMessage,
    resetChatSender,
    sendingChatId,
    setChatError,
  };
}
