import { useEffect, useState, type FormEvent } from "react"
import type { AuthService } from "../../services"
import {
  errorAsyncState,
  idleAsyncState,
  pendingAsyncState,
  successAsyncState,
  type AsyncState,
} from "../../services/asyncState"
import { normalizeError, validationError } from "../../services/errors"

export function LoginScreen({
  username,
  password,
  error,
  pending = false,
  onUsernameChange,
  onPasswordChange,
  onSubmit,
  onSignUp,
  onForgotPassword,
}: {
  username: string
  password: string
  error: string
  pending?: boolean
  onUsernameChange: (value: string) => void
  onPasswordChange: (value: string) => void
  onSubmit: (event: FormEvent<HTMLFormElement>) => void | Promise<void>
  onSignUp: () => void
  onForgotPassword: () => void
}) {
  const canSubmit = username.length > 0 && password.length > 0

  return (
    <main className="login-page">
      <div className="login-glow login-glow-left" aria-hidden="true" />
      <div className="login-glow login-glow-right" aria-hidden="true" />

      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand">
          <span className="login-logo" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
                fill="white"
              />
            </svg>
          </span>
          <span>LocalChat</span>
        </div>

        <div className="login-heading">
          <h1 id="login-title">Welcome back</h1>
          <p>Sign in to continue to your conversations.</p>
        </div>

        <form onSubmit={onSubmit} className="login-form">
          <label htmlFor="login-username">Username</label>
          <input
            id="login-username"
            name="username"
            type="text"
            autoComplete="username"
            autoFocus
            value={username}
            onChange={(event) => onUsernameChange(event.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "login-error login-hint" : "login-hint"}
            placeholder="Enter your username"
          />

          <div className="login-password-label">
            <label htmlFor="login-password">Password</label>
            <button type="button" onClick={onForgotPassword}>
              Forgot password?
            </button>
          </div>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => onPasswordChange(event.target.value)}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? "login-error login-hint" : "login-hint"}
            placeholder="Enter your password"
          />

          {error && (
            <p id="login-error" className="login-error" role="alert">
              {error}
            </p>
          )}

          <button type="submit" disabled={!canSubmit || pending}>
            {pending ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div className="login-signup-section">
          <span>New to LocalChat?</span>
          <button type="button" onClick={onSignUp}>
            Sign up
          </button>
        </div>

        <p id="login-hint" className="login-hint">
          Sign in with the local account created during setup.
        </p>
      </section>
    </main>
  )
}

export function SignupScreen({
  authService,
  initialStep = "methods",
  onEmailSignup,
  onBackToMethods,
  onBackToLogin,
  onSignupComplete,
}: {
  authService: AuthService
  initialStep?: "methods" | "email"
  onEmailSignup?: () => void
  onBackToMethods?: () => void
  onBackToLogin: () => void
  onSignupComplete: () => void
}) {
  const [step, setStep] =
    useState<"methods" | "email" | "verify" | "password" | "success">(
      initialStep,
    )
  const [selectedMethod, setSelectedMethod] = useState<string | null>(null)
  const [email, setEmail] = useState("")
  const [verificationCode, setVerificationCode] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [signupRequestState, setSignupRequestState] =
    useState<AsyncState<unknown>>(() => idleAsyncState())
  const [codeSecondsRemaining, setCodeSecondsRemaining] = useState(0)
  const [resendSecondsRemaining, setResendSecondsRemaining] = useState(0)
  const signupError = signupRequestState.error?.message ?? ""
  const isSubmitting = signupRequestState.status === "pending"

  const signupMethods = [
    { id: "email", badge: "@", label: "Sign up with email" },
    { id: "google", badge: "G", label: "Continue with Google" },
    { id: "company", badge: "SSO", label: "Continue with company" },
  ]

  const passwordRequirements = [
    { label: "At least 8 characters", met: newPassword.length >= 8 },
    { label: "One uppercase letter", met: /[A-Z]/.test(newPassword) },
    { label: "One lowercase letter", met: /[a-z]/.test(newPassword) },
    { label: "One number", met: /[0-9]/.test(newPassword) },
    { label: "One special character", met: /[^A-Za-z0-9]/.test(newPassword) },
  ]
  const passwordsMatch =
    newPassword.length > 0 && newPassword === confirmPassword
  const passwordIsValid =
    passwordRequirements.every((requirement) => requirement.met) &&
    passwordsMatch

  useEffect(() => {
    if (step !== "verify") return
    const timer = window.setInterval(() => {
      setCodeSecondsRemaining((current) => Math.max(0, current - 1))
      setResendSecondsRemaining((current) => Math.max(0, current - 1))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [step])

  const submitEmail = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSignupRequestState(pendingAsyncState())
    try {
      await authService.requestEmailVerification(email)
      setSignupRequestState(successAsyncState({ email }))
      setCodeSecondsRemaining(5 * 60)
      setResendSecondsRemaining(30)
      setStep("verify")
    } catch (error) {
      setSignupRequestState(errorAsyncState(normalizeError(error)))
    }
  }

  const submitVerificationCode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (codeSecondsRemaining === 0) {
      setSignupRequestState(
        errorAsyncState(
          validationError(
            "That verification code has expired. Request a new code.",
          ),
        ),
      )
      return
    }
    setSignupRequestState(pendingAsyncState())
    try {
      await authService.verifyEmailCode({ email, code: verificationCode })
      setSignupRequestState(successAsyncState({ email }))
      setStep("password")
    } catch (error) {
      setSignupRequestState(errorAsyncState(normalizeError(error)))
    }
  }

  const submitPassword = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!passwordIsValid) {
      setSignupRequestState(
        errorAsyncState(
          validationError(
            "Complete every password requirement and make sure both passwords match.",
          ),
        ),
      )
      return
    }
    setSignupRequestState(pendingAsyncState())
    try {
      await authService.createAccount({ email, password: newPassword })
      setSignupRequestState(successAsyncState({ email }))
      setStep("success")
    } catch (error) {
      setSignupRequestState(errorAsyncState(normalizeError(error)))
    }
  }

  const resendCode = async () => {
    if (resendSecondsRemaining > 0 || isSubmitting) return
    setSignupRequestState(pendingAsyncState())
    try {
      await authService.requestEmailVerification(email)
      setVerificationCode("")
      setSignupRequestState(successAsyncState({ email }))
      setCodeSecondsRemaining(5 * 60)
      setResendSecondsRemaining(30)
    } catch (error) {
      setSignupRequestState(errorAsyncState(normalizeError(error)))
    }
  }

  const beginOAuth = async (provider: "google" | "company", label: string) => {
    setSignupRequestState(pendingAsyncState())
    try {
      const redirect = await authService.getOAuthRedirect(provider, "/chat")
      setSelectedMethod(`${label} redirect ready: ${redirect.url}`)
      setSignupRequestState(successAsyncState(redirect))
    } catch (error) {
      setSignupRequestState(errorAsyncState(normalizeError(error)))
    }
  }

  const stepHeading = {
    methods: ["Create your account", "Choose how you would like to sign up."],
    email: ["Sign up with email", "Start with the demo email address below."],
    verify: ["Check your email", `Enter the verification code for ${email}.`],
    password: [
      "Create a password",
      "Choose a strong password for your new account.",
    ],
    success: ["Account created", "Your demo account is ready to use."],
  }[step]

  return (
    <main className="login-page">
      <div className="login-glow login-glow-left" aria-hidden="true" />
      <div className="login-glow login-glow-right" aria-hidden="true" />

      <section
        className="login-card signup-card"
        aria-labelledby="signup-title"
      >
        <div className="login-brand">
          <span className="login-logo" aria-hidden="true">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path
                d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"
                fill="white"
              />
            </svg>
          </span>
          <span>LocalChat</span>
        </div>

        {step !== "methods" && step !== "success" && (
          <button
            type="button"
            className="signup-step-back"
            onClick={() => {
              setSignupRequestState(idleAsyncState())
              if (step === "email" && onBackToMethods) {
                onBackToMethods()
                return
              }
              setStep(
                step === "password"
                  ? "verify"
                  : step === "verify"
                    ? "email"
                    : "methods",
              )
            }}
          >
            ← Back
          </button>
        )}

        <div className="login-heading signup-heading">
          <h1 id="signup-title">{stepHeading[0]}</h1>
          <p>{stepHeading[1]}</p>
        </div>

        {step === "methods" && (
          <>
            <div className="signup-options">
              {signupMethods.map((method) => (
                <button
                  key={method.id}
                  type="button"
                  onClick={() => {
                    setSignupRequestState(idleAsyncState())
                    if (method.id === "email") {
                      setSelectedMethod(null)
                      if (onEmailSignup) onEmailSignup()
                      else setStep("email")
                    } else {
                      void beginOAuth(
                        method.id as "google" | "company",
                        method.label,
                      )
                    }
                  }}
                  className={
                    selectedMethod === method.label
                      ? "signup-option signup-option-selected"
                      : "signup-option"
                  }
                >
                  <span
                    className={`signup-method-badge signup-method-${method.id}`}
                    aria-hidden="true"
                  >
                    {method.badge}
                  </span>
                  <span>{method.label}</span>
                  <span className="signup-option-arrow" aria-hidden="true">
                    →
                  </span>
                </button>
              ))}
            </div>
            {selectedMethod && (
              <p className="signup-placeholder" role="status">
                {selectedMethod} is a visual placeholder for now.
              </p>
            )}
          </>
        )}

        {step === "email" && (
          <form className="login-form email-signup-form" onSubmit={submitEmail}>
            <label htmlFor="signup-email">Email address</label>
            <input
              id="signup-email"
              type="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(event) => {
                setEmail(event.target.value)
                setSignupRequestState(idleAsyncState())
              }}
              placeholder="test@email.com"
              aria-invalid={Boolean(signupError)}
            />
            <p className="signup-info-note">
              A code will be sent to your email.
            </p>
            {signupError && (
              <p className="login-error" role="alert">
                {signupError}
              </p>
            )}
            <button type="submit" disabled={!email || isSubmitting}>
              {isSubmitting ? "Sending code…" : "Sign up"}
            </button>
          </form>
        )}

        {step === "verify" && (
          <form
            className="login-form email-signup-form"
            onSubmit={submitVerificationCode}
          >
            <div className="signup-sent-notice" role="status">
              A verification code was sent to <strong>{email}</strong>.
            </div>
            <label htmlFor="signup-code">Verification code</label>
            <input
              id="signup-code"
              className="verification-code-input"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              autoFocus
              maxLength={5}
              value={verificationCode}
              onChange={(event) => {
                setVerificationCode(event.target.value.replace(/\D/g, ""))
                setSignupRequestState(idleAsyncState())
              }}
              placeholder="12345"
              aria-invalid={Boolean(signupError)}
            />
            <p className="signup-info-note">
              Use <strong>12345</strong> for this demo.
            </p>
            <p className="signup-info-note" aria-live="polite">
              {codeSecondsRemaining > 0
                ? `Code expires in ${Math.floor(codeSecondsRemaining / 60)}:${String(
                    codeSecondsRemaining % 60,
                  ).padStart(2, "0")}`
                : "Code expired"}
            </p>
            {signupError && (
              <p className="login-error" role="alert">
                {signupError}
              </p>
            )}
            <button
              type="submit"
              disabled={verificationCode.length !== 5 || isSubmitting}
            >
              {isSubmitting ? "Verifying…" : "Verify code"}
            </button>
            <button
              type="button"
              className="signup-secondary-action"
              onClick={() => void resendCode()}
              disabled={resendSecondsRemaining > 0 || isSubmitting}
            >
              {resendSecondsRemaining > 0
                ? `Resend code in ${resendSecondsRemaining}s`
                : "Resend code"}
            </button>
          </form>
        )}

        {step === "password" && (
          <form
            className="login-form email-signup-form"
            onSubmit={submitPassword}
          >
            <label htmlFor="signup-password">Create password</label>
            <input
              id="signup-password"
              type="password"
              autoComplete="new-password"
              autoFocus
              value={newPassword}
              onChange={(event) => {
                setNewPassword(event.target.value)
                setSignupRequestState(idleAsyncState())
              }}
              placeholder="Create a strong password"
            />
            <label
              htmlFor="signup-password-confirm"
              className="confirm-password-label"
            >
              Confirm password
            </label>
            <input
              id="signup-password-confirm"
              type="password"
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(event) => {
                setConfirmPassword(event.target.value)
                setSignupRequestState(idleAsyncState())
              }}
              placeholder="Enter your password again"
            />

            <div
              className="password-requirements"
              aria-label="Password requirements"
            >
              <strong>Password requirements</strong>
              <ul>
                {passwordRequirements.map((requirement) => (
                  <li
                    key={requirement.label}
                    className={requirement.met ? "requirement-met" : ""}
                  >
                    <span aria-hidden="true">
                      {requirement.met ? "✓" : "○"}
                    </span>{" "}
                    {requirement.label}
                  </li>
                ))}
                <li className={passwordsMatch ? "requirement-met" : ""}>
                  <span aria-hidden="true">{passwordsMatch ? "✓" : "○"}</span>{" "}
                  Passwords match
                </li>
              </ul>
            </div>
            {signupError && (
              <p className="login-error" role="alert">
                {signupError}
              </p>
            )}
            <button type="submit" disabled={!passwordIsValid || isSubmitting}>
              {isSubmitting ? "Creating account…" : "Create account"}
            </button>
          </form>
        )}

        {step === "success" && (
          <div className="signup-success">
            <div className="signup-success-icon" aria-hidden="true">
              ✓
            </div>
            <p>Email verified and password created successfully.</p>
            <button type="button" onClick={onSignupComplete}>
              Continue to LocalChat
            </button>
          </div>
        )}

        {step === "methods" && (
          <button
            type="button"
            onClick={onBackToLogin}
            className="signup-back-button"
          >
            Already have an account? <strong>Sign in</strong>
          </button>
        )}
      </section>
    </main>
  )
}
