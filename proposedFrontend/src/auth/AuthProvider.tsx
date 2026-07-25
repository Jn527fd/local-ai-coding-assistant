import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import type { SignInRequest } from "../domain/dtos"
import type { AuthSession } from "../domain/models"
import { appServices } from "../services"
import {
  errorAsyncState,
  pendingAsyncState,
  successAsyncState,
  type AsyncState,
} from "../services/asyncState"
import { normalizeError } from "../services/errors"

type AuthStatus = "restoring" | "authenticated" | "unauthenticated"

interface AuthContextValue {
  session: AuthSession | null
  status: AuthStatus
  signIn(input: SignInRequest): Promise<AuthSession>
  signOut(): Promise<void>
  refreshSession(): Promise<AuthSession | null>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [sessionState, setSessionState] =
    useState<AsyncState<AuthSession | null>>(() => pendingAsyncState())
  const session = sessionState.data ?? null
  const status: AuthStatus =
    sessionState.status === "pending" && sessionState.data === undefined
      ? "restoring"
      : session
        ? "authenticated"
        : "unauthenticated"

  const refreshSession = useCallback(async () => {
    setSessionState(pendingAsyncState(session))
    const restored = await appServices.auth.restoreSession()
    setSessionState(successAsyncState(restored))
    return restored
  }, [session])

  useEffect(() => {
    let active = true
    void appServices.auth
      .restoreSession()
      .then((restored) => {
        if (!active) return
        setSessionState(successAsyncState(restored))
      })
      .catch((error) => {
        if (!active) return
        setSessionState(errorAsyncState(normalizeError(error), null))
      })

    return () => {
      active = false
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      session,
      status,
      async signIn(input) {
        const authenticatedSession = await appServices.auth.signIn(input)
        setSessionState(successAsyncState(authenticatedSession))
        return authenticatedSession
      },
      async signOut() {
        setSessionState(pendingAsyncState(session))
        try {
          await appServices.auth.signOut()
        } finally {
          setSessionState(successAsyncState(null))
        }
      },
      refreshSession,
    }),
    [refreshSession, session, status],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used inside AuthProvider.")
  return context
}
