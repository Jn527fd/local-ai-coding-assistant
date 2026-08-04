import { Link } from "react-router-dom"

export function SessionLoadingScreen() {
  return (
    <main className="login-page" aria-busy="true">
      <div className="login-glow login-glow-left" aria-hidden="true" />
      <div className="login-glow login-glow-right" aria-hidden="true" />
      <section className="login-card route-status-card" aria-live="polite">
        <span className="login-logo" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path
              d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
              fill="white"
            />
          </svg>
        </span>
        <h1>Restoring your session</h1>
        <p>Please wait while LocalChat checks your demo session.</p>
        <div className="route-loading-indicator" aria-hidden="true" />
      </section>
    </main>
  )
}

export function ProtectedPlaceholder({
  title,
  description,
  linkTo = "/chat",
  linkLabel = "Back to chat",
}: {
  title: string
  description: string
  linkTo?: string
  linkLabel?: string
}) {
  return (
    <main className="login-page">
      <div className="login-glow login-glow-left" aria-hidden="true" />
      <div className="login-glow login-glow-right" aria-hidden="true" />
      <section className="login-card route-status-card">
        <span className="login-logo" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path
              d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
              fill="white"
            />
          </svg>
        </span>
        <h1>{title}</h1>
        <p>{description}</p>
        <Link to={linkTo} className="route-primary-link">
          {linkLabel}
        </Link>
      </section>
    </main>
  )
}

export function NotFoundScreen() {
  return (
    <main className="login-page">
      <div className="login-glow login-glow-left" aria-hidden="true" />
      <div className="login-glow login-glow-right" aria-hidden="true" />
      <section className="login-card route-status-card">
        <span className="route-error-code">404</span>
        <h1>Page not found</h1>
        <p>The page you requested does not exist in this frontend demo.</p>
        <Link to="/" className="route-primary-link">
          Return to LocalChat
        </Link>
      </section>
    </main>
  )
}
