import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  checkHealth,
  deleteConversation as deletePersistedConversation,
  getCurrentUser,
  getModelStatus,
  importConversations,
  indexDocument,
  listConversations,
  listDocumentIndexes,
  listDocuments,
  logout,
  processDocument,
  searchDocuments,
  sendChatStream,
  uploadDocument,
} from "./api.js";
import {
  buildDefaultConversationSettings,
  chatStorageKey,
  createChat,
  loadChats,
  loadConversationPersistenceMode,
  MAX_CHATS,
  normalizeChats,
  normalizeConversationSettings,
  PERSISTENCE_MODE_BACKEND,
  PERSISTENCE_MODE_LOCAL,
  saveConversationPersistenceMode,
  titleFromMessage,
} from "./chatState.js";
import AccountPanel from "./components/AccountPanel.jsx";
import AppLayout from "./components/AppLayout.jsx";
import CommandPalette from "./components/CommandPalette.jsx";
import Composer from "./components/Composer.jsx";
import LoginPage from "./components/LoginPage.jsx";
import NavigationRail from "./components/NavigationRail.jsx";
import Workspace from "./components/Workspace.jsx";
import { Button, Input, Modal, Toast } from "./components/ui.jsx";
import { useCapabilities } from "./hooks/useCapabilities.js";

const API_KEY_STORAGE_KEY = "local-ai-coding-assistant.api-key";

function App() {
  const composerRef = useRef(null);

  const [authState, setAuthState] = useState("checking");
  const [user, setUser] = useState(null);
  const [apiKey, setApiKey] = useState(
    () => window.localStorage.getItem(API_KEY_STORAGE_KEY) || "",
  );
  const [accountOpen, setAccountOpen] = useState(false);
  const [modelStatus, setModelStatus] = useState(null);
  const {
    capabilities,
    capabilitiesStatus,
    refreshCapabilities,
    resetCapabilities,
  } = useCapabilities();
  const [apiStatus, setApiStatus] = useState({
    status: "checking",
    message: "Checking backend connection...",
  });

  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState("");
  const [conversationPersistenceMode, setConversationPersistenceMode] = useState(
    PERSISTENCE_MODE_LOCAL,
  );
  const [conversationPersistenceStatus, setConversationPersistenceStatus] =
    useState("Browser-local storage");
  const [sendingChatId, setSendingChatId] = useState("");
  const [documentsByChat, setDocumentsByChat] = useState({});
  const [documentIndexesByChat, setDocumentIndexesByChat] = useState({});
  const [documentBusy, setDocumentBusy] = useState(false);
  const [documentError, setDocumentError] = useState("");
  const [indexingDocumentId, setIndexingDocumentId] = useState("");
  const [documentSearchQuery, setDocumentSearchQuery] = useState("");
  const [documentSearchResults, setDocumentSearchResults] = useState([]);
  const [documentSearchWarnings, setDocumentSearchWarnings] = useState([]);
  const [documentSearchBusy, setDocumentSearchBusy] = useState(false);
  const [documentSearchError, setDocumentSearchError] = useState("");
  const [draftMessage, setDraftMessage] = useState("");
  const [chatError, setChatError] = useState("");
  const [toast, setToast] = useState(null);
  const [chatDialog, setChatDialog] = useState({
    chatId: "",
    mode: "",
    value: "",
  });

  const [currentSection, setCurrentSection] = useState("ask");
  const [recentsDrawerOpen, setRecentsDrawerOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

  const activeChat = useMemo(
    () => chats.find((chat) => chat.id === activeChatId) || null,
    [activeChatId, chats],
  );
  const activeDocuments = useMemo(
    () => documentsByChat[activeChatId] || [],
    [activeChatId, documentsByChat],
  );
  const activeDocumentIndexes = useMemo(
    () => documentIndexesByChat[activeChatId] || [],
    [activeChatId, documentIndexesByChat],
  );
  const dialogChat = useMemo(
    () => chats.find((chat) => chat.id === chatDialog.chatId) || null,
    [chatDialog.chatId, chats],
  );
  const defaultConversationSettings = useMemo(
    () =>
      buildDefaultConversationSettings({
        capabilities,
      }),
    [capabilities],
  );

  const focusComposer = useCallback((nextMessage = "") => {
    if (nextMessage) {
      setDraftMessage(nextMessage);
    }
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }, []);

  const showToast = useCallback((message, tone = "info") => {
    const id = window.crypto?.randomUUID?.() || String(Date.now());
    setToast({ id, message, tone });
    window.setTimeout(() => {
      setToast((current) => (current?.id === id ? null : current));
    }, 3200);
  }, []);

  const refreshModelStatus = useCallback(async () => {
    const status = await getModelStatus();
    setModelStatus(status);
    return status;
  }, []);

  const refreshApiStatus = useCallback(async () => {
    setApiStatus({
      status: "checking",
      message: "Checking backend connection...",
    });

    try {
      const result = await checkHealth();
      if (result?.status === "ok") {
        setApiStatus({ status: "online", message: "FastAPI is online" });
      } else {
        setApiStatus({
          status: "offline",
          message: "Backend returned an unexpected response.",
        });
      }
    } catch (error) {
      setApiStatus({ status: "offline", message: error.message });
    }
  }, []);

  const refreshDocuments = useCallback(
    async (conversationId) => {
      if (!apiKey || !conversationId) {
        return [];
      }

      try {
        const result = await listDocuments(apiKey, conversationId);
        const documents = Array.isArray(result?.documents) ? result.documents : [];
        setDocumentsByChat((current) => ({
          ...current,
          [conversationId]: documents,
        }));
        return documents;
      } catch (error) {
        setDocumentError(error.message);
        return [];
      }
    },
    [apiKey],
  );

  const refreshDocumentIndexes = useCallback(
    async (conversationId) => {
      if (!apiKey || !conversationId) {
        return [];
      }

      try {
        const result = await listDocumentIndexes(apiKey, conversationId);
        const indexes = Array.isArray(result?.indexes) ? result.indexes : [];
        setDocumentIndexesByChat((current) => ({
          ...current,
          [conversationId]: indexes,
        }));
        return indexes;
      } catch (error) {
        setDocumentSearchError(error.message);
        return [];
      }
    },
    [apiKey],
  );

  const initializeAuthenticatedSession = useCallback(
    async (session) => {
      const [modelResult, capabilitiesResult] = await Promise.allSettled([
        refreshModelStatus(),
        refreshCapabilities(),
        refreshApiStatus(),
      ]);
      const nextModelStatus =
        modelResult.status === "fulfilled" ? modelResult.value : null;
      const nextCapabilities =
        capabilitiesResult.status === "fulfilled"
          ? capabilitiesResult.value
          : null;
      const defaults = buildDefaultConversationSettings({
        capabilities: nextCapabilities,
      });
      const requestedMode = loadConversationPersistenceMode(session.username);
      let savedChats = loadChats(session.username, defaults);
      let activePersistenceMode = requestedMode;
      let persistenceStatus = "Browser-local storage";

      if (requestedMode === PERSISTENCE_MODE_BACKEND) {
        try {
          const result = await listConversations();
          savedChats = normalizeChats(result?.conversations || [], defaults);
          persistenceStatus = "Backend persistence active";
        } catch (error) {
          activePersistenceMode = PERSISTENCE_MODE_LOCAL;
          saveConversationPersistenceMode(session.username, PERSISTENCE_MODE_LOCAL);
          persistenceStatus = "Backend persistence unavailable; using browser storage";
          showToast(error.message, "error");
        }
      }

      setUser(session);
      setChats(savedChats);
      setActiveChatId(savedChats[0]?.id || "");
      setConversationPersistenceMode(activePersistenceMode);
      setConversationPersistenceStatus(persistenceStatus);
      setAuthState("authenticated");
    },
    [refreshApiStatus, refreshCapabilities, refreshModelStatus, showToast],
  );

  useEffect(() => {
    async function restoreSession() {
      try {
        const session = await getCurrentUser();
        await initializeAuthenticatedSession(session);
      } catch {
        setUser(null);
        setAuthState("anonymous");
        resetCapabilities();
        setConversationPersistenceMode(PERSISTENCE_MODE_LOCAL);
        setConversationPersistenceStatus("Browser-local storage");
      }
    }

    restoreSession();
  }, [initializeAuthenticatedSession, resetCapabilities]);

  useEffect(() => {
    if (authState !== "authenticated") {
      return;
    }

    setChats((current) => {
      const normalized = normalizeChats(current, defaultConversationSettings);
      return JSON.stringify(normalized) === JSON.stringify(current)
        ? current
        : normalized;
    });
  }, [authState, defaultConversationSettings]);

  useEffect(() => {
    if (authState !== "authenticated" || !user) {
      return;
    }

    window.localStorage.setItem(chatStorageKey(user.username), JSON.stringify(chats));
  }, [authState, chats, user]);

  useEffect(() => {
    if (
      authState !== "authenticated" ||
      !user ||
      conversationPersistenceMode !== PERSISTENCE_MODE_BACKEND
    ) {
      return undefined;
    }

    const timeoutId = window.setTimeout(() => {
      importConversations(chats, { replace: true })
        .then(() => {
          setConversationPersistenceStatus("Backend persistence active");
        })
        .catch((error) => {
          saveConversationPersistenceMode(user.username, PERSISTENCE_MODE_LOCAL);
          setConversationPersistenceMode(PERSISTENCE_MODE_LOCAL);
          setConversationPersistenceStatus(
            "Backend persistence unavailable; using browser storage",
          );
          showToast(error.message, "error");
        });
    }, 500);

    return () => window.clearTimeout(timeoutId);
  }, [authState, chats, conversationPersistenceMode, showToast, user]);

  useEffect(() => {
    if (authState !== "authenticated" || !activeChatId || !apiKey) {
      return;
    }

    refreshDocuments(activeChatId);
    refreshDocumentIndexes(activeChatId);
    setDocumentSearchResults([]);
    setDocumentSearchWarnings([]);
    setDocumentSearchError("");
  }, [
    activeChatId,
    apiKey,
    authState,
    refreshDocumentIndexes,
    refreshDocuments,
  ]);

  useEffect(() => {
    if (authState !== "authenticated") {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      refreshApiStatus();
      refreshModelStatus().catch(() => setModelStatus(null));
    }, 15000);

    return () => window.clearInterval(intervalId);
  }, [authState, refreshApiStatus, refreshModelStatus]);

  function handleLogin(session) {
    initializeAuthenticatedSession(session);
  }

  async function handleLogout() {
    try {
      await logout();
    } finally {
      setAccountOpen(false);
      setUser(null);
      setAuthState("anonymous");
      setModelStatus(null);
      resetCapabilities();
      setChats([]);
      setActiveChatId("");
      setConversationPersistenceMode(PERSISTENCE_MODE_LOCAL);
      setConversationPersistenceStatus("Browser-local storage");
      setDocumentsByChat({});
      setDocumentIndexesByChat({});
      setDocumentBusy(false);
      setDocumentError("");
      setIndexingDocumentId("");
      setDocumentSearchQuery("");
      setDocumentSearchResults([]);
      setDocumentSearchWarnings([]);
      setDocumentSearchBusy(false);
      setDocumentSearchError("");
      setDraftMessage("");
    }
  }

  function handleApiKeyChange(nextKey) {
    setApiKey(nextKey);
    window.localStorage.setItem(API_KEY_STORAGE_KEY, nextKey);
  }

  const handleEnableBackendPersistence = useCallback(async () => {
    if (!user) {
      return false;
    }

    const normalized = normalizeChats(chats, defaultConversationSettings);
    setConversationPersistenceStatus("Migrating browser chats...");
    try {
      const result = await importConversations(normalized, { replace: true });
      const backendChats = normalizeChats(
        result?.conversations || normalized,
        defaultConversationSettings,
      );
      saveConversationPersistenceMode(user.username, PERSISTENCE_MODE_BACKEND);
      setConversationPersistenceMode(PERSISTENCE_MODE_BACKEND);
      setConversationPersistenceStatus("Backend persistence active");
      setChats(backendChats);
      if (!backendChats.some((chat) => chat.id === activeChatId)) {
        setActiveChatId(backendChats[0]?.id || "");
      }
      showToast("Browser chats migrated to backend storage.", "success");
      return true;
    } catch (error) {
      saveConversationPersistenceMode(user.username, PERSISTENCE_MODE_LOCAL);
      setConversationPersistenceMode(PERSISTENCE_MODE_LOCAL);
      setConversationPersistenceStatus(
        "Backend persistence unavailable; using browser storage",
      );
      showToast(error.message, "error");
      return false;
    }
  }, [
    activeChatId,
    chats,
    defaultConversationSettings,
    showToast,
    user,
  ]);

  const handleUseBrowserPersistence = useCallback(() => {
    if (!user) {
      return;
    }

    saveConversationPersistenceMode(user.username, PERSISTENCE_MODE_LOCAL);
    setConversationPersistenceMode(PERSISTENCE_MODE_LOCAL);
    setConversationPersistenceStatus("Browser-local storage");
    showToast("Using browser-local conversation storage.", "success");
  }, [showToast, user]);

  const getActiveConversationSettings = useCallback(
    () => normalizeConversationSettings(activeChat?.settings, defaultConversationSettings),
    [activeChat, defaultConversationSettings],
  );

  const activeConversationSettings = useMemo(
    () => getActiveConversationSettings(),
    [getActiveConversationSettings],
  );

  const updateConversationSettings = useCallback(
    (conversationId, patch) => {
      setChats((current) =>
        current.map((chat) =>
          chat.id === conversationId
            ? {
                ...chat,
                settings: normalizeConversationSettings(
                  {
                    ...chat.settings,
                    ...patch,
                  },
                  defaultConversationSettings,
                ),
                updatedAt: new Date().toISOString(),
              }
            : chat,
        ),
      );
    },
    [defaultConversationSettings],
  );

  const updateActiveConversationSettings = useCallback(
    (patch) => {
      if (!activeChatId) {
        return;
      }
      updateConversationSettings(activeChatId, patch);
    },
    [activeChatId, updateConversationSettings],
  );

  const rememberDocument = useCallback((conversationId, document) => {
    if (!conversationId || !document?.documentId) {
      return;
    }

    setDocumentsByChat((current) => {
      const existing = current[conversationId] || [];
      const withoutDocument = existing.filter(
        (item) => item.documentId !== document.documentId,
      );
      return {
        ...current,
        [conversationId]: [document, ...withoutDocument],
      };
    });
  }, []);

  const handleUploadDocument = useCallback(
    async (file) => {
      if (!apiKey) {
        setDocumentError("Save and verify your API key before uploading documents.");
        return false;
      }

      if (!activeChat) {
        setDocumentError("Create a chat before uploading documents.");
        return false;
      }

      const extension = file.name.split(".").pop()?.toLowerCase() || "";
      if (!["txt", "md", "pdf"].includes(extension)) {
        setDocumentError("Only .txt, .md, and .pdf files are supported.");
        return false;
      }

      const conversationId = activeChat.id;
      const conversationSettings = normalizeConversationSettings(
        activeChat.settings,
        defaultConversationSettings,
      );

      setDocumentBusy(true);
      setDocumentError("");

      try {
        const uploaded = await uploadDocument(
          apiKey,
          conversationId,
          file,
          conversationSettings,
        );
        rememberDocument(conversationId, uploaded);

        const processed = await processDocument(
          apiKey,
          uploaded.documentId,
          conversationId,
          conversationSettings,
        );
        const processedDocument = processed.document || uploaded;
        rememberDocument(conversationId, processedDocument);
        await refreshDocuments(conversationId);

        if (processed.status === "processed") {
          showToast(
            `${processedDocument.originalFilename || file.name} processed (${processed.chunkCount || 0} chunks).`,
            "success",
          );
        } else {
          setDocumentError(processed.error || "Document processing failed.");
          showToast("Document uploaded, but processing failed.", "error");
        }
        return processed.status === "processed";
      } catch (error) {
        setDocumentError(error.message);
        showToast("Document upload failed.", "error");
        return false;
      } finally {
        setDocumentBusy(false);
      }
    },
    [
      activeChat,
      apiKey,
      defaultConversationSettings,
      refreshDocuments,
      rememberDocument,
      showToast,
    ],
  );

  const handleIndexDocument = useCallback(
    async (document) => {
      if (!apiKey) {
        setDocumentSearchError("Save and verify your API key before indexing documents.");
        return false;
      }

      if (!activeChat || !document?.documentId) {
        return false;
      }

      if (document.status !== "processed") {
        setDocumentSearchError("Process the document before indexing it.");
        return false;
      }

      const conversationSettings = normalizeConversationSettings(
        activeChat.settings,
        defaultConversationSettings,
      );
      setIndexingDocumentId(document.documentId);
      setDocumentSearchError("");

      try {
        const result = await indexDocument(
          apiKey,
          document.documentId,
          activeChat.id,
          conversationSettings,
        );
        await refreshDocumentIndexes(activeChat.id);
        showToast(
          `${document.originalFilename || "Document"} indexed (${result.indexedChunks || 0} chunks).`,
          "success",
        );
        return true;
      } catch (error) {
        setDocumentSearchError(error.message);
        showToast("Document indexing failed.", "error");
        return false;
      } finally {
        setIndexingDocumentId("");
      }
    },
    [
      activeChat,
      apiKey,
      defaultConversationSettings,
      refreshDocumentIndexes,
      showToast,
    ],
  );

  const handleSearchDocuments = useCallback(async () => {
    const query = documentSearchQuery.trim();
    if (!query) {
      setDocumentSearchError("");
      setDocumentSearchResults([]);
      return false;
    }

    if (!apiKey) {
      setDocumentSearchError("Save and verify your API key before searching documents.");
      return false;
    }

    if (!activeChat) {
      setDocumentSearchError("Create a chat before searching documents.");
      return false;
    }

    const conversationSettings = normalizeConversationSettings(
      activeChat.settings,
      defaultConversationSettings,
    );
    setDocumentSearchBusy(true);
    setDocumentSearchError("");
    setDocumentSearchWarnings([]);

    try {
      const result = await searchDocuments(
        apiKey,
        activeChat.id,
        query,
        conversationSettings,
        { topK: 5 },
      );
      setDocumentSearchResults(
        Array.isArray(result?.results) ? result.results : [],
      );
      setDocumentSearchWarnings(
        Array.isArray(result?.warnings) ? result.warnings : [],
      );
      return true;
    } catch (error) {
      setDocumentSearchError(error.message);
      setDocumentSearchResults([]);
      return false;
    } finally {
      setDocumentSearchBusy(false);
    }
  }, [
    activeChat,
    apiKey,
    defaultConversationSettings,
    documentSearchQuery,
  ]);

  const handleNewChat = useCallback(() => {
    if (chats.length >= MAX_CHATS) {
      setChatError("You already have five chats. Delete one before creating another.");
      return;
    }

    const nextChat = createChat(defaultConversationSettings);
    setChats((current) => [nextChat, ...current]);
    setActiveChatId(nextChat.id);
    setChatError("");
    setDocumentError("");
    setCurrentSection("ask");
    setDraftMessage("");
    setDocumentSearchQuery("");
    setDocumentSearchResults([]);
    setDocumentSearchWarnings([]);
    setDocumentSearchError("");
    focusComposer();
    showToast("New private thread ready.", "success");
  }, [chats.length, defaultConversationSettings, focusComposer, showToast]);

  function handleDeleteChat(chatId = activeChat?.id) {
    const targetChat = chats.find((chat) => chat.id === chatId);
    if (!targetChat) {
      return;
    }

    setChatDialog({ chatId: targetChat.id, mode: "delete", value: "" });
  }

  async function confirmDeleteChat() {
    const targetChat = dialogChat;
    if (!targetChat) {
      setChatDialog({ chatId: "", mode: "", value: "" });
      return;
    }

    setChats((current) => {
      const remaining = current.filter((chat) => chat.id !== targetChat.id);
      if (remaining.length === 0) {
        const replacement = createChat(defaultConversationSettings);
        setActiveChatId(replacement.id);
        return [replacement];
      }

      if (targetChat.id === activeChatId) {
        setActiveChatId(remaining[0].id);
      }
      return remaining;
    });

    if (targetChat.id === activeChatId) {
      setChatError("");
      setDraftMessage("");
    }
    showToast("Thread deleted.", "success");
    setChatDialog({ chatId: "", mode: "", value: "" });

    if (conversationPersistenceMode === PERSISTENCE_MODE_BACKEND) {
      try {
        await deletePersistedConversation(targetChat.id);
      } catch (error) {
        setConversationPersistenceStatus(
          "Backend delete failed; browser copy was removed",
        );
        showToast(error.message, "error");
      }
    }
  }

  function handleRenameChat(chatId = activeChat?.id) {
    const targetChat = chats.find((chat) => chat.id === chatId);
    if (!targetChat) {
      return;
    }

    setChatDialog({ chatId: targetChat.id, mode: "rename", value: targetChat.title });
  }

  function confirmRenameChat(event) {
    event?.preventDefault();
    const targetChat = dialogChat;
    const nextTitle = chatDialog.value.trim();

    if (!targetChat || !nextTitle) {
      return;
    }

    setChats((current) =>
      current.map((chat) =>
        chat.id === targetChat.id
          ? { ...chat, title: nextTitle, updatedAt: new Date().toISOString() }
          : chat,
      ),
    );
    showToast("Thread renamed.", "success");
    setChatDialog({ chatId: "", mode: "", value: "" });
  }

  function handleExportActiveChat() {
    if (!activeChat) {
      return;
    }

    const transcript = activeChat.messages
      .map((message) => `${message.role.toUpperCase()}\n${message.content}`)
      .join("\n\n---\n\n");
    const blob = new Blob([`# ${activeChat.title}\n\n${transcript}\n`], {
      type: "text/markdown",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${activeChat.title.replace(/[^a-z0-9_-]+/gi, "-").toLowerCase() || "thread"}.md`;
    link.click();
    URL.revokeObjectURL(url);
    showToast("Thread exported as Markdown.", "success");
  }

  function handleDeleteMessage(messageIndex) {
    if (!activeChat) {
      return;
    }

    setChats((current) =>
      current.map((chat) =>
        chat.id === activeChat.id
          ? {
              ...chat,
              messages: chat.messages.filter((_, index) => index !== messageIndex),
              updatedAt: new Date().toISOString(),
            }
          : chat,
      ),
    );
    showToast("Message removed from this thread.", "success");
  }

  async function handleSendMessage(message, imageAttachments = []) {
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
                chat.messages.length === 0 ? titleFromMessage(message) : chat.title,
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
                        generationTimeMs: Math.max(0, Math.round(generationEndedAt - generationStartedAt)),
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
  }

  function handleOpenModelSettings() {
    setCurrentSection("settings");
    setAccountOpen(true);
  }

  function handleOpenSourceDetails(source) {
    showToast(`Source: ${source}`, "info");
  }

  function runCommand(commandId) {
    if (commandId === "ask-codebase") {
      setCurrentSection("ask");
      focusComposer();
    } else if (commandId === "switch-model") {
      handleOpenModelSettings();
    } else if (commandId === "settings") {
      setAccountOpen(true);
    } else if (commandId === "clear-thread") {
      handleDeleteChat();
    } else if (commandId === "new-chat") {
      handleNewChat();
    } else if (commandId === "focus-composer") {
      focusComposer();
    } else if (commandId === "toggle-sidebar") {
      setRecentsDrawerOpen((current) => !current);
    }
  }

  useEffect(() => {
    function handleKeyboard(event) {
      const hasModifier = event.metaKey || event.ctrlKey;
      if (!hasModifier) {
        if (event.key === "Escape") {
          setCommandOpen(false);
          setAccountOpen(false);
          setRecentsDrawerOpen(false);
          setChatDialog({ chatId: "", mode: "", value: "" });
        }
        return;
      }

      const key = event.key.toLowerCase();
      if (key === "k") {
        event.preventDefault();
        setCommandOpen((current) => !current);
      } else if (key === "n") {
        event.preventDefault();
        handleNewChat();
      } else if (key === "l") {
        event.preventDefault();
        composerRef.current?.focus();
      }
    }

    window.addEventListener("keydown", handleKeyboard);
    return () => window.removeEventListener("keydown", handleKeyboard);
  }, [handleNewChat]);

  if (authState === "checking") {
    return (
      <main className="login-shell login-shell--loading">
        <section className="login-card">
          <span className="brand-mark">LA</span>
          <p>Checking local session...</p>
        </section>
      </main>
    );
  }

  if (authState !== "authenticated" || !user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  const navigation = (
    <NavigationRail
        activeChatId={activeChatId}
        chats={chats}
        currentSection={currentSection}
        drawerOpen={recentsDrawerOpen}
        onCloseDrawer={() => setRecentsDrawerOpen(false)}
        onDeleteChat={handleDeleteChat}
        onNewChat={handleNewChat}
        onOpenSettings={() => setAccountOpen(true)}
        onRenameChat={handleRenameChat}
        onSelectChat={(chatId) => {
          setActiveChatId(chatId);
          setCurrentSection("ask");
          setChatError("");
          setDocumentError("");
          setDraftMessage("");
          setDocumentSearchQuery("");
          setDocumentSearchResults([]);
          setDocumentSearchWarnings([]);
          setDocumentSearchError("");
          setRecentsDrawerOpen(false);
        }}
        onSelectSection={setCurrentSection}
        onToggleDrawer={() => setRecentsDrawerOpen((current) => !current)}
      />
  );

  const toastNode = toast ? (
    <div className="toast-stack" aria-live="polite">
      <Toast className={`toast toast--${toast.tone}`} tone={toast.tone}>
        {toast.message}
      </Toast>
    </div>
  ) : null;

  const composer = (
    <Composer
      activeChat={activeChat}
      composerRef={composerRef}
      documentError={documentError}
      documentIndexes={activeDocumentIndexes}
      documents={activeDocuments}
      documentSearchBusy={documentSearchBusy}
      documentSearchError={documentSearchError}
      documentSearchQuery={documentSearchQuery}
      documentSearchResults={documentSearchResults}
      documentSearchWarnings={documentSearchWarnings}
      indexingDocumentId={indexingDocumentId}
      isUploadingDocument={documentBusy}
      isSending={sendingChatId === activeChatId}
      message={draftMessage}
      onIndexDocument={handleIndexDocument}
      onMessageChange={setDraftMessage}
      onSearchDocuments={handleSearchDocuments}
      onSearchQueryChange={setDocumentSearchQuery}
      onSendMessage={handleSendMessage}
      onUploadDocument={handleUploadDocument}
    />
  );

  const chatDialogNode = chatDialog.mode ? (
    <Modal
      className="confirmation-dialog"
      overlayClassName="dialog-overlay"
      title={chatDialog.mode === "delete" ? "Delete thread" : "Rename thread"}
    >
      {chatDialog.mode === "delete" ? (
        <>
          <div className="confirmation-dialog__copy">
            <p className="section-kicker">Delete thread</p>
            <h2>Erase this local conversation?</h2>
            <p>
              "{dialogChat?.title || "This thread"}" and its browser-stored
              history will be removed. Your other chats stay untouched.
            </p>
          </div>
          <div className="confirmation-dialog__actions">
            <Button
              onClick={() => setChatDialog({ chatId: "", mode: "", value: "" })}
              type="button"
              variant="ghost"
            >
              Cancel
            </Button>
            <Button onClick={confirmDeleteChat} type="button" variant="danger">
              Delete thread
            </Button>
          </div>
        </>
      ) : (
        <form className="confirmation-dialog__form" onSubmit={confirmRenameChat}>
          <div className="confirmation-dialog__copy">
            <p className="section-kicker">Rename thread</p>
            <h2>Name this conversation</h2>
            <p>Use a short title that will still make sense in your recent list.</p>
          </div>
          <label className="field">
            <span className="field__label">Thread title</span>
            <Input
              autoFocus
              onChange={(event) =>
                setChatDialog((current) => ({ ...current, value: event.target.value }))
              }
              value={chatDialog.value}
            />
          </label>
          <div className="confirmation-dialog__actions">
            <Button
              onClick={() => setChatDialog({ chatId: "", mode: "", value: "" })}
              type="button"
              variant="ghost"
            >
              Cancel
            </Button>
            <Button disabled={!chatDialog.value.trim()} type="submit" variant="primary">
              Save title
            </Button>
          </div>
        </form>
      )}
    </Modal>
  ) : null;

  return (
    <AppLayout
      accountPanel={
        <AccountPanel
          activeConversationSettings={activeConversationSettings}
          activeConversationTitle={activeChat?.title || "Untitled thread"}
          apiKey={apiKey}
          capabilities={capabilities}
          capabilitiesStatus={capabilitiesStatus}
          conversationPersistenceMode={conversationPersistenceMode}
          conversationPersistenceStatus={conversationPersistenceStatus}
          isOpen={accountOpen}
          onApiKeyChange={handleApiKeyChange}
          onClose={() => setAccountOpen(false)}
          onConversationSettingsChange={updateActiveConversationSettings}
          onConversationSettingsVerified={(title) =>
            showToast(`Settings verified for "${title}".`, "success")
          }
          onEnableBackendPersistence={handleEnableBackendPersistence}
          onLogout={handleLogout}
          onModelStatus={setModelStatus}
          onRefreshCapabilities={refreshCapabilities}
          onUseBrowserPersistence={handleUseBrowserPersistence}
          username={user.username}
        />
      }
      className={`app-layout--reference-chat ${
        activeChat?.messages?.length ? "" : "app-layout--empty-chat"
      }`}
      commandPalette={
        <CommandPalette
          isOpen={commandOpen}
          onClose={() => setCommandOpen(false)}
          onRunCommand={runCommand}
        />
      }
      composer={composer}
      contextDrawer={null}
      dialogs={chatDialogNode}
      header={null}
      navigation={navigation}
      toast={toastNode}
    >
      <Workspace
          activeChat={activeChat}
          error={chatError}
          isSending={sendingChatId === activeChatId}
          onDeleteChat={handleDeleteChat}
          onDeleteMessage={handleDeleteMessage}
          onExportChat={handleExportActiveChat}
          onOpenSourceDetails={handleOpenSourceDetails}
          onRenameChat={handleRenameChat}
        />
    </AppLayout>
  );
}

export default App;
