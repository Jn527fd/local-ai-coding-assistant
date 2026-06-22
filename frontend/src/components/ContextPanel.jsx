function HealthRow({ label, status, detail }) {
  const isOnline = status === "online" || status === "connected";
  const isChecking = status === "checking";

  return (
    <div className="health-row">
      <span
        className={`status-dot ${
          isChecking
            ? "status-dot--checking"
            : isOnline
              ? "status-dot--online"
              : "status-dot--offline"
        }`}
      />
      <div>
        <strong>{label}</strong>
        <small>{detail}</small>
      </div>
    </div>
  );
}

function ContextPanel({
  apiBaseUrl,
  apiStatus,
  collapsed,
  indexedRepository,
  indexingProgress,
  modelStatus,
  onIndexRepository,
  onOpenAccount,
  onToggleCollapsed,
}) {
  if (collapsed) {
    return null;
  }

  const activeModel = modelStatus?.active_model || "No active model";
  const ollamaStatus = modelStatus?.ollama_connected
    ? "connected"
    : modelStatus
      ? "offline"
      : "checking";
  const fastApiDetail =
    apiStatus.status === "online"
      ? "FastAPI is online"
      : apiStatus.status === "checking"
        ? "Checking backend..."
        : apiStatus.message;

  return (
    <aside className="context-panel" aria-label="Workspace context">
      <div className="context-panel__header">
        <div>
          <span className="header-kicker">Context</span>
          <h2>Workspace state</h2>
        </div>
        <button
          className="icon-control"
          onClick={onToggleCollapsed}
          type="button"
        >
          Hide
        </button>
      </div>

      <section className="context-card">
        <div className="context-card__heading">
          <span>Active model</span>
          <span className="context-tag">Ollama</span>
        </div>
        <strong className="context-card__title">{activeModel}</strong>
        <p>Provider: Ollama</p>
        <p>Status: {modelStatus?.ollama_connected ? "connected" : "checking"}</p>
        <button className="ghost-button" onClick={onOpenAccount} type="button">
          Manage models
        </button>
      </section>

      <section className="context-card">
        <div className="context-card__heading">
          <span>Codebase context</span>
          <span className="context-tag">Local files</span>
        </div>
        <strong className="context-card__title">
          {indexedRepository?.name || "No repository indexed"}
        </strong>
        <dl className="mini-metrics">
          <div>
            <dt>Indexed files</dt>
            <dd>{indexedRepository?.indexedFiles ?? 0}</dd>
          </div>
          <div>
            <dt>Last indexed</dt>
            <dd>{indexedRepository?.lastIndexedAt || "Never"}</dd>
          </div>
        </dl>
        {indexingProgress?.phase !== "idle" && (
          <p className="empty-copy">{indexingProgress.message}</p>
        )}
        <button className="secondary-button" onClick={onIndexRepository} type="button">
          {indexedRepository ? "Reindex" : "Index a local repository"}
        </button>
      </section>

      <section className="context-card">
        <div className="context-card__heading">
          <span>Retrieval</span>
          <span className="context-tag">RAG</span>
        </div>
        <dl className="detail-stack">
          <div>
            <dt>Mode</dt>
            <dd>Semantic + keyword</dd>
          </div>
          <div>
            <dt>Top-k</dt>
            <dd>5 chunks</dd>
          </div>
        </dl>
      </section>

      <section className="context-card">
        <div className="context-card__heading">
          <span>Citations</span>
          <span className="context-tag">Sources</span>
        </div>
        <p className="empty-copy">
          Citations will appear here after grounded codebase answers.
        </p>
      </section>

      <section className="context-card">
        <div className="context-card__heading">
          <span>Runtime health</span>
          <span className="context-tag">Local</span>
        </div>
        <div className="health-list">
          <HealthRow
            detail={fastApiDetail}
            label="FastAPI"
            status={apiStatus.status}
          />
          <HealthRow
            detail={ollamaStatus === "connected" ? "Ollama connected" : "Check Ollama service"}
            label="Ollama"
            status={ollamaStatus}
          />
          <div className="endpoint-row">
            <span>Endpoint</span>
            <code>{apiBaseUrl}</code>
          </div>
        </div>
      </section>
    </aside>
  );
}

export default ContextPanel;
