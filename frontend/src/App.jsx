import { useState } from "react";

import { API_BASE_URL } from "./api.js";
import ChatBox from "./components/ChatBox.jsx";
import RepoIndexer from "./components/RepoIndexer.jsx";
import StatusPanel from "./components/StatusPanel.jsx";

function App() {
  const [apiKey, setApiKey] = useState("");
  const [showApiKey, setShowApiKey] = useState(false);

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

        <div className="privacy-badge" aria-label="Local processing">
          <span className="privacy-badge__dot" />
          Local-first
        </div>
      </header>

      <main className="main-layout">
        <aside className="sidebar">
          <StatusPanel apiBaseUrl={API_BASE_URL} />

          <section className="panel credential-panel">
            <div className="panel__heading">
              <div>
                <p className="section-kicker">Authentication</p>
                <h2>API key</h2>
              </div>
            </div>

            <p className="muted">
              Enter the same value configured as <code>API_KEY</code> in
              <code> backend/.env</code>. It stays in this browser tab only.
            </p>

            <label className="field">
              <span className="field__label">Bearer key</span>
              <div className="secret-input">
                <input
                  autoComplete="off"
                  onChange={(event) => setApiKey(event.target.value)}
                  placeholder="Paste your API key"
                  type={showApiKey ? "text" : "password"}
                  value={apiKey}
                />
                <button
                  className="text-button"
                  onClick={() => setShowApiKey((current) => !current)}
                  type="button"
                >
                  {showApiKey ? "Hide" : "Show"}
                </button>
              </div>
            </label>

            <div className={`key-state ${apiKey ? "key-state--ready" : ""}`}>
              <span className="key-state__dot" />
              {apiKey ? "Key ready for protected requests" : "API key required"}
            </div>
          </section>
        </aside>

        <div className="workspace">
          <ChatBox apiKey={apiKey} />
          <RepoIndexer apiKey={apiKey} />
        </div>
      </main>

      <footer>
        FastAPI + React + Ollama. Your repository stays on your machine.
      </footer>
    </div>
  );
}

export default App;
