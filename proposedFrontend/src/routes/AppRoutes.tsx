import { Navigate, Route, Routes } from "react-router-dom"
import { useAuth } from "../auth/AuthProvider"
import ChatPage from "../App"
import { LoginRoute, SignupRoute } from "./AuthRoutes"
import { ProtectedRoute } from "./ProtectedRoute"
import { DiagnosticsPage } from "../features/diagnostics/DiagnosticsPage"
import { ProfilePage } from "../features/profile/ProfilePage"
import { RepositoryPage } from "../features/repositories/RepositoryPage"
import { SettingsPage } from "../features/settings/SettingsPage"
import {
  NotFoundScreen,
  ProtectedPlaceholder,
  SessionLoadingScreen,
} from "./RouteScreens"

function HomeRoute() {
  const auth = useAuth()
  if (auth.status === "restoring") return <SessionLoadingScreen />
  return (
    <Navigate
      to={auth.status === "authenticated" ? "/chat" : "/login"}
      replace
    />
  )
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomeRoute />} />
      <Route path="/login" element={<LoginRoute />} />
      <Route path="/signup" element={<SignupRoute />} />
      <Route path="/signup/email" element={<SignupRoute emailOnly />} />
      <Route
        path="/forgot-password"
        element={
          <ProtectedPlaceholder
            title="Forgot password"
            description="Password recovery is represented by this route contract and will connect to the authentication backend later."
            linkTo="/login"
            linkLabel="Back to sign in"
          />
        }
      />
      <Route
        path="/reset-password"
        element={
          <ProtectedPlaceholder
            title="Reset password"
            description="A valid backend reset token will open the password reset workflow here."
            linkTo="/login"
            linkLabel="Back to sign in"
          />
        }
      />

      <Route element={<ProtectedRoute />}>
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:conversationId" element={<ChatPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/repositories" element={<RepositoryPage />} />
        <Route path="/diagnostics" element={<DiagnosticsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route
          path="/help"
          element={
            <ProtectedPlaceholder
              title="Help"
              description="Help content will be implemented in a later phase."
            />
          }
        />
      </Route>

      <Route path="*" element={<NotFoundScreen />} />
    </Routes>
  )
}
