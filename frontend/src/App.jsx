import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { checkHealth, getCurrentUser, getModelStatus, logout, sendChat } from "./api.js";
import {
  chatStorageKey,
  createChat,
  loadChats,
  MAX_CHATS,
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
  const [apiStatus, setApiStatus] = useState({
    status: "checking",
    message: "Checking backend connection...",
  });

  const [chats, setChats] = useState([]);
  const [activeChatId, setActiveChatId] = useState("");
  const [sendingChatId, setSendingChatId] = useState("");
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
  const dialogChat = useMemo(
    () => chats.find((chat) => chat.id === chatDialog.chatId) || null,
    [chatDialog.chatId, chats],
  );
  const activeModel = modelStatus?.active_model || "";

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

  useEffect(() => {
    async function restoreSession() {
      try {
        const session = await getCurrentUser();
        const savedChats = loadChats(session.username);
        setUser(session);
        setChats(savedChats);
        setActiveChatId(savedChats[0]?.id || "");
        setAuthState("authenticated");
        await Promise.allSettled([refreshModelStatus(), refreshApiStatus()]);
      } catch {
        setUser(null);
        setAuthState("anonymous");
      }
    }

    restoreSession();
  }, [refreshApiStatus, refreshModelStatus]);

  useEffect(() => {
    if (authState !== "authenticated" || !user) {
      return;
    }

    window.localStorage.setItem(chatStorageKey(user.username), JSON.stringify(chats));
  }, [authState, chats, user]);

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
    const savedChats = loadChats(session.username);
    setUser(session);
    setChats(savedChats);
    setActiveChatId(savedChats[0]?.id || "");
    setAuthState("authenticated");
    refreshModelStatus().catch(() => setModelStatus(null));
    refreshApiStatus();
  }

  async function handleLogout() {
    try {
      await logout();
    } finally {
      setAccountOpen(false);
      setUser(null);
      setAuthState("anonymous");
      setModelStatus(null);
      setChats([]);
      setActiveChatId("");
      setDraftMessage("");
    }
  }

  function handleApiKeyChange(nextKey) {
    setApiKey(nextKey);
    window.localStorage.setItem(API_KEY_STORAGE_KEY, nextKey);
  }

  const handleNewChat = useCallback(() => {
    if (chats.length >= MAX_CHATS) {
      setChatError("You already have five chats. Delete one before creating another.");
      return;
    }

    const nextChat = createChat();
    setChats((current) => [nextChat, ...current]);
    setActiveChatId(nextChat.id);
    setChatError("");
    setCurrentSection("ask");
    setDraftMessage("");
    focusComposer();
    showToast("New private thread ready.", "success");
  }, [chats.length, focusComposer, showToast]);

  function handleDeleteChat(chatId = activeChat?.id) {
    const targetChat = chats.find((chat) => chat.id === chatId);
    if (!targetChat) {
      return;
    }

    setChatDialog({ chatId: targetChat.id, mode: "delete", value: "" });
  }

  function confirmDeleteChat() {
    const targetChat = dialogChat;
    if (!targetChat) {
      setChatDialog({ chatId: "", mode: "", value: "" });
      return;
    }

    setChats((current) => {
      const remaining = current.filter((chat) => chat.id !== targetChat.id);
      if (remaining.length === 0) {
        const replacement = createChat();
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

  async function handleSendMessage(message) {
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
      createdAt: new Date().toISOString(),
    };

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
              messages: [...chat.messages, userMessage],
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
      const result = await sendChat(apiKey, message, history);
      const generationEndedAt =
        typeof globalThis.performance?.now === "function"
          ? globalThis.performance.now()
          : Date.now();
      const sources = Array.isArray(result.sources) ? result.sources : [];
      setChats((current) =>
        current.map((chat) =>
          chat.id === chatId
            ? {
                ...chat,
                messages: [
                  ...chat.messages,
                  {
                    role: "assistant",
                    content: result.answer,
                    generationTimeMs: Math.max(0, Math.round(generationEndedAt - generationStartedAt)),
                    model: result.model || result.model_used || activeModel || "Local model",
                    sources,
                    createdAt: new Date().toISOString(),
                  },
                ],
                updatedAt: new Date().toISOString(),
              }
            : chat,
        ),
      );
      return true;
    } catch (requestError) {
      setChatError(requestError.message);
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
          setDraftMessage("");
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
      isSending={sendingChatId === activeChatId}
      message={draftMessage}
      onMessageChange={setDraftMessage}
      onSendMessage={handleSendMessage}
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
          apiKey={apiKey}
          isOpen={accountOpen}
          onApiKeyChange={handleApiKeyChange}
          onClose={() => setAccountOpen(false)}
          onLogout={handleLogout}
          onModelStatus={setModelStatus}
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
