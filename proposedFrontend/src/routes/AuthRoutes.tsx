import { useState, type FormEvent } from "react"
import { Navigate, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../auth/AuthProvider"
import { LoginScreen, SignupScreen } from "../features/auth/AuthScreens"
import { appServices } from "../services"
import type { AuthSession } from "../domain/models"
import {
  errorAsyncState,
  idleAsyncState,
  pendingAsyncState,
  successAsyncState,
  type AsyncState,
} from "../services/asyncState"
import { normalizeError } from "../services/errors"
import { SessionLoadingScreen } from "./RouteScreens"

interface RedirectState {
  from?: string
}

export function LoginRoute() {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as RedirectState | null)?.from ?? "/chat"
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [signInState, setSignInState] = useState<AsyncState<AuthSession>>(() =>
    idleAsyncState(),
  )

  if (auth.status === "restoring") return <SessionLoadingScreen />
  if (auth.status === "authenticated") {
    return <Navigate to={redirectTo} replace />
  }

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setSignInState(pendingAsyncState())
    try {
      const session = await auth.signIn({ username, password })
      setPassword("")
      setSignInState(successAsyncState(session))
      navigate(redirectTo, { replace: true })
    } catch (caughtError) {
      setSignInState(errorAsyncState(normalizeError(caughtError)))
    }
  }

  return (
    <LoginScreen
      username={username}
      password={password}
      error={signInState.error?.message ?? ""}
      pending={signInState.status === "pending"}
      onUsernameChange={(value) => {
        setUsername(value)
        setSignInState(idleAsyncState())
      }}
      onPasswordChange={(value) => {
        setPassword(value)
        setSignInState(idleAsyncState())
      }}
      onSubmit={submit}
      onSignUp={() => navigate("/signup", { state: { from: redirectTo } })}
      onForgotPassword={() => navigate("/forgot-password")}
    />
  )
}

export function SignupRoute({ emailOnly = false }: { emailOnly?: boolean }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as RedirectState | null)?.from ?? "/chat"

  if (auth.status === "restoring") return <SessionLoadingScreen />
  if (auth.status === "authenticated") {
    return <Navigate to={redirectTo} replace />
  }

  return (
    <SignupScreen
      key={emailOnly ? "email" : "methods"}
      authService={appServices.auth}
      initialStep={emailOnly ? "email" : "methods"}
      onEmailSignup={
        emailOnly
          ? undefined
          : () => navigate("/signup/email", { state: { from: redirectTo } })
      }
      onBackToMethods={
        emailOnly
          ? () => navigate("/signup", { state: { from: redirectTo } })
          : undefined
      }
      onBackToLogin={() =>
        navigate("/login", { replace: true, state: { from: redirectTo } })
      }
      onSignupComplete={() => {
        void auth.refreshSession().then(() => {
          navigate(redirectTo, { replace: true })
        })
      }}
    />
  )
}
