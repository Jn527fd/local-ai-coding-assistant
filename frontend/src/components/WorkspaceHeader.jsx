function WorkspaceHeader({
  activeModel,
  indexedRepository,
  onOpenAccount,
  onOpenCommandPalette,
  onToggleContextPanel,
  username,
}) {
  const repositoryLabel = indexedRepository?.name || "No repository indexed";

  return (
    <header className="workspace-header">
      <div className="workspace-header__title">
        <span className="header-kicker">Private workspace</span>
        <strong>Local AI Coding Assistant</strong>
      </div>

      <div className="header-repository" title={repositoryLabel}>
        <span className="header-repository__label">Codebase</span>
        <span>{repositoryLabel}</span>
      </div>

      <div className="workspace-header__actions">
        <button
          className="header-model-button"
          onClick={onOpenAccount}
          type="button"
        >
          <span className="status-dot status-dot--online" />
          {activeModel || "Select model"}
        </button>
        <span className="privacy-badge">
          <span className="privacy-badge__dot" />
          Local only
        </span>
        <button
          className="command-button"
          onClick={onOpenCommandPalette}
          type="button"
        >
          Command <kbd>⌘K</kbd>
        </button>
        <button
          aria-label="Toggle context panel"
          className="icon-control"
          onClick={onToggleContextPanel}
          type="button"
        >
          Panel
        </button>
        <button
          aria-label="Open account settings"
          className="avatar-button"
          onClick={onOpenAccount}
          title={`Account: ${username}`}
          type="button"
        >
          {username.slice(0, 1).toUpperCase()}
        </button>
      </div>
    </header>
  );
}

export default WorkspaceHeader;
