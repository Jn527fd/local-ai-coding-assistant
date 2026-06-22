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
    <main className="login-page">
      <section className="login-card">
        <div className="login-card__brand">
          <div className="empty-state__mark">&gt;_</div>
          <p className="eyebrow">Private developer workspace</p>
          <h1>Welcome back</h1>
          <p>
            Sign in with a user from your local credentials file. Your
            password is verified by the FastAPI service on this machine.
          </p>
        </div>

        <form className="stacked-form login-form" onSubmit={handleSubmit}>
          <label className="field">
            <span className="field__label">Username</span>
            <input
              autoComplete="username"
              autoFocus
              onChange={(event) => setUsername(event.target.value)}
              value={username}
            />
          </label>

          <label className="field">
            <span className="field__label">Password</span>
            <input
              autoComplete="current-password"
              onChange={(event) => setPassword(event.target.value)}
              type="password"
              value={password}
            />
          </label>

          {error && <div className="alert alert--error">{error}</div>}

          <button
            className="primary-button login-button"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="login-card__hint">
          Credentials are stored locally and are never sent to a cloud
          authentication provider.
        </p>
      </section>
    </main>
  );
}

export default LoginPage;
