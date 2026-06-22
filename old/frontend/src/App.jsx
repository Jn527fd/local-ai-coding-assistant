import { useEffect, useState } from "react";

import { API_BASE_URL, getCurrentUser, getModelStatus, logout } from "./api.js";
import AccountPanel from "./components/AccountPanel.jsx";
import ChatBox from "./components/ChatBox.jsx";
import LoginPage from "./components/LoginPage.jsx";
import RepoIndexer from "./components/RepoIndexer.jsx";
import StatusPanel from "./components/StatusPanel.jsx";

const API_KEY_STORAGE_KEY = "local-ai-coding-assistant.api-key";

function App() {
  const [authState, setAuthState] = useState("checking");
  const [user, setUser] = useState(null);
  const [apiKey, setApiKey] = useState(
    () => window.localStorage.getItem(API_KEY_STORAGE_KEY) || "",
  );
  const [accountOpen, setAccountOpen] = useState(false);
  const [modelStatus, setModelStatus] = useState(null);

  useEffect(() => {
    async function restoreSession() {
      try {
        const session = await getCurrentUser();
        setUser(session);
        setAuthState("authenticated");
        try {
          setModelStatus(await getModelStatus());
        } catch {
          setModelStatus(null);
        }
      } catch {
        setUser(null);
        setAuthState("anonymous");
      }
    }

    restoreSession();
  }, []);

  function handleLogin(session) {
    setUser(session);
    setAuthState("authenticated");
    getModelStatus().then(setModelStatus).catch(() => setModelStatus(null));
  }

  async function handleLogout() {
    try {
      await logout();
    } finally {
      setAccountOpen(false);
      setUser(null);
      setAuthState("anonymous");
      setModelStatus(null);
    }
  }

  function handleApiKeyChange(nextKey) {
    setApiKey(nextKey);
    window.localStorage.setItem(API_KEY_STORAGE_KEY, nextKey);
  }

  if (authState === "checking") {
    return (
      <main className="login-page">
        <section className="login-card login-card--loading">
          <div className="empty-state__mark">&gt;_</div>
          <p>Checking local session...</p>
        </section>
      </main>
    );
  }

  if (authState !== "authenticated" || !user) {
    return <LoginPage onLogin={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <header className="hero">
        <div className="hero__content">
          <p className="eyebrow">Self-hosted developer workspace</p>
          <h1>Local AI Coding Assistant</h1>
          <p className="hero__description">
            Chat with Ollama, index a local codebase, and ask grounded
            questions without sending your source code to a cloud model.
          </p>
        </div>

        <div className="hero__actions">
          <div className="privacy-badge" aria-label="Local processing">
            <span className="privacy-badge__dot" />
            Local-first
          </div>
          <button
            aria-label="Open account settings"
            className="avatar-button"
            onClick={() => setAccountOpen(true)}
            title={`Account: ${user.username}`}
            type="button"
          >
            {user.username.slice(0, 1).toUpperCase()}
          </button>
        </div>
      </header>

      <main className="main-layout">
        <aside className="sidebar">
          <StatusPanel
            activeModel={modelStatus?.active_model}
            apiBaseUrl={API_BASE_URL}
          />

          <section className="panel credential-panel">
            <div className="panel__heading">
              <div>
                <p className="section-kicker">Protected requests</p>
                <h2>API connection</h2>
              </div>
            </div>

            <p className="muted">
              Manage and verify your persistent API key from the account
              button in the top-right corner.
            </p>

            <div className={`key-state ${apiKey ? "key-state--ready" : ""}`}>
              <span className="key-state__dot" />
              {apiKey ? "Local API key saved" : "API key setup required"}
            </div>

            <button
              className="secondary-button sidebar-button"
              onClick={() => setAccountOpen(true)}
              type="button"
            >
              Open account settings
            </button>
          </section>
        </aside>

        <div className="workspace">
          <ChatBox
            activeModel={modelStatus?.active_model}
            apiKey={apiKey}
            username={user.username}
          />
          <RepoIndexer apiKey={apiKey} />
        </div>
      </main>

      <footer>
        FastAPI + React + Ollama. Your repository stays on your machine.
      </footer>

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
