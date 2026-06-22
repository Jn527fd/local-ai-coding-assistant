import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  API_BASE_URL,
  checkHealth,
  getCurrentUser,
  getModelStatus,
  logout,
  sendChat,
} from "./api.js";
import {
  chatStorageKey,
  createChat,
  loadChats,
  MAX_CHATS,
  titleFromMessage,
} from "./chatState.js";
import AccountPanel from "./components/AccountPanel.jsx";
import ChatBox from "./components/ChatBox.jsx";
import CommandPalette from "./components/CommandPalette.jsx";
import ContextPanel from "./components/ContextPanel.jsx";
import LoginPage from "./components/LoginPage.jsx";
import WorkspaceHeader from "./components/WorkspaceHeader.jsx";
import WorkspaceSidebar from "./components/WorkspaceSidebar.jsx";

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
  const [chatError, setChatError] = useState("");
  const [workspaceNotice, setWorkspaceNotice] = useState("");

  const [currentSection, setCurrentSection] = useState("chat");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => window.matchMedia("(max-width: 900px)").matches,
  );
  const [contextCollapsed, setContextCollapsed] = useState(
    () => window.matchMedia("(max-width: 1180px)").matches,
  );
  const [commandOpen, setCommandOpen] = useState(false);
  const [indexedRepository, setIndexedRepository] = useState(null);
  const [indexingProgress, setIndexingProgress] = useState({
    phase: "idle",
    message: "Repository upload flow is pending.",
  });

  const activeChat = useMemo(
    () => chats.find((chat) => chat.id === activeChatId) || null,
    [activeChatId, chats],
  );
  const activeModel = modelStatus?.active_model || "";
  const hasIndexedRepository = Boolean(indexedRepository);

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
    setWorkspaceNotice("");
    setCurrentSection("chat");
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }, [chats.length]);

  function handleDeleteActiveChat() {
    if (!activeChat) {
      return;
    }

    const confirmed = window.confirm(
      `Delete "${activeChat.title}"? Its messages and model context will be erased from this browser.`,
    );
    if (!confirmed) {
      return;
    }

    setChats((current) => {
      const remaining = current.filter((chat) => chat.id !== activeChat.id);
      if (remaining.length === 0) {
        const replacement = createChat();
        setActiveChatId(replacement.id);
        return [replacement];
      }

      setActiveChatId(remaining[0].id);
      return remaining;
    });
    setChatError("");
    setWorkspaceNotice("");
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
    const userMessage = { role: "user", content: message };

    setChatError("");
    setWorkspaceNotice("");
    setSendingChatId(chatId);
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
      const result = await sendChat(apiKey, message, history);
      setChats((current) =>
        current.map((chat) =>
          chat.id === chatId
            ? {
                ...chat,
                messages: [
                  ...chat.messages,
                  { role: "assistant", content: result.answer },
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

  function handleIndexRepository() {
    setIndexingProgress({
      phase: "planned",
      message: "Repository indexing will return as a plus-button upload flow.",
    });
    setWorkspaceNotice(
      "Repository indexing is temporarily API-only while the upload workflow is redesigned.",
    );
    setCurrentSection("codebase");
  }

  function runCommand(commandId) {
    if (commandId === "new-chat") {
      handleNewChat();
    } else if (commandId === "focus-composer") {
      composerRef.current?.focus();
    } else if (commandId === "toggle-sidebar") {
      setSidebarCollapsed((current) => !current);
    } else if (commandId === "toggle-context") {
      setContextCollapsed((current) => !current);
    } else if (commandId === "settings") {
      setAccountOpen(true);
    }
  }

  useEffect(() => {
    function handleKeyboard(event) {
      const hasModifier = event.metaKey || event.ctrlKey;
      if (!hasModifier) {
        if (event.key === "Escape") {
          setCommandOpen(false);
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

  return (
    <div
      className={`workspace-shell ${
        sidebarCollapsed ? "workspace-shell--sidebar-collapsed" : ""
      } ${contextCollapsed ? "workspace-shell--context-collapsed" : ""}`}
    >
      <WorkspaceSidebar
        activeChatId={activeChatId}
        activeModel={activeModel}
        chats={chats}
        collapsed={sidebarCollapsed}
        currentSection={currentSection}
        isOllamaOnline={Boolean(modelStatus?.ollama_connected)}
        onNewChat={handleNewChat}
        onOpenSettings={() => setAccountOpen(true)}
        onSelectChat={(chatId) => {
          setActiveChatId(chatId);
          setCurrentSection("chat");
          setChatError("");
          setWorkspaceNotice("");
        }}
        onSelectSection={setCurrentSection}
        onToggleCollapsed={() => setSidebarCollapsed((current) => !current)}
      />

      <WorkspaceHeader
        activeModel={activeModel}
        indexedRepository={indexedRepository}
        onOpenAccount={() => setAccountOpen(true)}
        onOpenCommandPalette={() => setCommandOpen(true)}
        onToggleContextPanel={() => setContextCollapsed((current) => !current)}
        username={user.username}
      />

      <main className="chat-main-shell">
        <ChatBox
          activeChat={activeChat}
          activeModel={activeModel}
          composerRef={composerRef}
          error={chatError}
          hasIndexedRepository={hasIndexedRepository}
          indexedRepository={indexedRepository}
          isSending={sendingChatId === activeChatId}
          notice={workspaceNotice}
          onDeleteChat={handleDeleteActiveChat}
          onIndexRepository={handleIndexRepository}
          onSendMessage={handleSendMessage}
        />
      </main>

      <ContextPanel
        apiBaseUrl={API_BASE_URL}
        apiStatus={apiStatus}
        collapsed={contextCollapsed}
        indexedRepository={indexedRepository}
        indexingProgress={indexingProgress}
        modelStatus={modelStatus}
        onIndexRepository={handleIndexRepository}
        onOpenAccount={() => setAccountOpen(true)}
        onToggleCollapsed={() => setContextCollapsed(true)}
      />

      <nav className="mobile-nav" aria-label="Mobile navigation">
        <button onClick={() => setSidebarCollapsed(false)} type="button">
          Menu
        </button>
        <button onClick={handleNewChat} type="button">
          New
        </button>
        <button onClick={() => setContextCollapsed(false)} type="button">
          Context
        </button>
      </nav>

      <CommandPalette
        isOpen={commandOpen}
        onClose={() => setCommandOpen(false)}
        onRunCommand={runCommand}
      />

      <AccountPanel
        apiKey={apiKey}
        isOpen={accountOpen}
        onApiKeyChange={handleApiKeyChange}
        onClose={() => setAccountOpen(false)}
        onLogout={handleLogout}
        onModelStatus={setModelStatus}
        username={user.username}
      />
    </div>
  );
}

export default App;
