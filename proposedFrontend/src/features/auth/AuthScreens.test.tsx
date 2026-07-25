import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { LoginScreen, SignupScreen } from "./AuthScreens"
import { createMockServices } from "../../services/mock/createMockServices"

describe("authentication screens", () => {
  it("requires both login fields and displays service errors", async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn((event) => event.preventDefault())
    const { rerender } = render(
      <LoginScreen
        username=""
        password=""
        error=""
        pending={false}
        onUsernameChange={vi.fn()}
        onPasswordChange={vi.fn()}
        onSubmit={onSubmit}
        onSignUp={vi.fn()}
        onForgotPassword={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: "Sign in" })).toBeDisabled()
    rerender(
      <LoginScreen
        username="test"
        password="test"
        error="Incorrect credentials"
        pending={false}
        onUsernameChange={vi.fn()}
        onPasswordChange={vi.fn()}
        onSubmit={onSubmit}
        onSignUp={vi.fn()}
        onForgotPassword={vi.fn()}
      />,
    )
    expect(screen.getByRole("alert")).toHaveTextContent("Incorrect credentials")
    await user.click(screen.getByRole("button", { name: "Sign in" }))
    expect(onSubmit).toHaveBeenCalledOnce()
  })

  it("moves through email, verification, password, and success steps", async () => {
    const user = userEvent.setup()
    const bundle = createMockServices()
    bundle.control.setLatency(0)
    render(
      <SignupScreen
        authService={bundle.services.auth}
        initialStep="email"
        onBackToLogin={vi.fn()}
        onSignupComplete={vi.fn()}
      />,
    )

    await user.type(screen.getByLabelText("Email address"), "test@email.com")
    await user.click(screen.getByRole("button", { name: "Sign up" }))
    expect(
      await screen.findByLabelText("Verification code"),
    ).toBeInTheDocument()
    await user.type(screen.getByLabelText("Verification code"), "00000")
    await user.click(screen.getByRole("button", { name: /verify code/i }))
    expect(await screen.findByRole("alert")).toHaveTextContent("not correct")
    await user.clear(screen.getByLabelText("Verification code"))
    await user.type(screen.getByLabelText("Verification code"), "12345")
    await user.click(screen.getByRole("button", { name: /verify code/i }))
    expect(await screen.findByLabelText("Create password")).toBeInTheDocument()
    await user.type(screen.getByLabelText("Create password"), "Strong!123")
    await user.type(screen.getByLabelText("Confirm password"), "Strong!123")
    await user.click(screen.getByRole("button", { name: /create account/i }))
    expect(
      await screen.findByText(/password created successfully/i),
    ).toBeInTheDocument()
  })
})
