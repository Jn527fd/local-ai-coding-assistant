import { Button, IconButton, ShortcutKey } from "./ui.jsx";

function Header({
  isNavigationCollapsed,
  onOpenAccount,
  onOpenCommandPalette,
  onToggleNavigation,
  username,
}) {
  return (
    <header className="app-header workspace-header">
      <IconButton
        className="header-nav-toggle"
        label={isNavigationCollapsed ? "Open navigation" : "Close navigation"}
        onClick={onToggleNavigation}
        type="button"
      >
        Menu
      </IconButton>

      <div className="top-bar__title workspace-header__title">
        <span className="header-kicker">Private Workspace</span>
      </div>

      <Button
        aria-label="Open command palette"
        className="header-command-trigger"
        onClick={onOpenCommandPalette}
        type="button"
        variant="ghost"
      >
        <span>Search, ask, or run a command...</span>
        <ShortcutKey>Ctrl K</ShortcutKey>
      </Button>

      <div className="top-bar__actions workspace-header__actions">
        <IconButton
          className="avatar-button"
          label="Open account settings"
          onClick={onOpenAccount}
          title={`Account: ${username}`}
          type="button"
        >
          {username.slice(0, 1).toUpperCase()}
        </IconButton>
      </div>
    </header>
  );
}

export default Header;
