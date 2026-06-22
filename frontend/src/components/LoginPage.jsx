import { useState } from "react";

import { login } from "../api.js";

function LoginPage({ onLogin }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!username.trim() || !password) {
      setError("Enter your username and password.");
      return;
    }

    setError("");
    setIsSubmitting(true);
    try {
      const session = await login(username.trim(), password);
      setPassword("");
      onLogin(session);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-hero" aria-labelledby="login-product-title">
        <div className="terminal-texture" aria-hidden="true">
          <span>$ ollama list</span>
          <span>$ index ./workspace</span>
          <span>$ ask --local</span>
        </div>
        <div className="login-hero__content">
          <span className="brand-mark">LA</span>
          <p className="header-kicker">Self-hosted AI workspace</p>
          <h1 id="login-product-title">Local AI Coding Assistant</h1>
          <p className="login-tagline">
            Private coding intelligence for your machine.
          </p>
          <ul className="trust-list">
            <li>No cloud authentication</li>
            <li>Source code stays local</li>
            <li>Powered by your local Ollama models</li>
          </ul>
        </div>
      </section>

      <section className="login-panel" aria-label="Sign in">
        <form className="login-card" onSubmit={handleSubmit}>
          <div className="login-card__heading">
            <p className="header-kicker">Account</p>
            <h2>Sign in locally</h2>
            <p>Use a user from your local credentials file.</p>
          </div>

          <label className="field" htmlFor="username">
            <span className="field__label">Username</span>
            <input
              autoComplete="username"
              autoFocus
              id="username"
              onChange={(event) => setUsername(event.target.value)}
              value={username}
            />
          </label>

          <label className="field" htmlFor="password">
            <span className="field__label">Password</span>
            <input
              autoComplete="current-password"
              id="password"
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </label>

          {error && (
            <div className="alert alert--error" role="alert">
              {error}
            </div>
          )}

          <button
            className="primary-button login-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>

          <p className="login-card__note">
            Credentials are verified by the local FastAPI service.
          </p>
        </form>
      </section>
    </main>
  );
}

export default LoginPage;
