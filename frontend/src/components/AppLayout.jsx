function AppLayout({
  accountPanel,
  children,
  className = "",
  commandPalette,
  composer,
  contextDrawer,
  dialogs,
  header,
  navigation,
  toast,
}) {
  return (
    <div className={`app-layout ${className}`}>
      {header}
      {navigation}
      {children}
      <div className="composer-region">{composer}</div>
      {contextDrawer}
      {toast}
      {commandPalette}
      {accountPanel}
      {dialogs}
    </div>
  );
}

export default AppLayout;
