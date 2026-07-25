import { Navigate, Outlet, useLocation } from "react-router-dom"
import { useAuth } from "../auth/AuthProvider"
import { SessionLoadingScreen } from "./RouteScreens"

export function ProtectedRoute() {
  const auth = useAuth()
  const location = useLocation()

  if (auth.status === "restoring") return <SessionLoadingScreen />
  if (auth.status === "unauthenticated") {
    return (
      <Navigate
        to="/login"
        replace
        state={{
          from: `${location.pathname}${location.search}${location.hash}`,
        }}
      />
    )
  }

  return <Outlet />
}
