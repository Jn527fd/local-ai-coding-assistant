import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { describe, expect, it, vi } from "vitest";

import App from "../App.jsx";
import CommandPalette from "../components/CommandPalette.jsx";

function seedApiKey() {
  window.localStorage.setItem("local-ai-coding-assistant.api-key", "test-key");
}

describe("accessibility", () => {
  it("has no critical axe violations on the authenticated main screen", async () => {
    seedApiKey();
    const { container } = render(<App />);
    await screen.findByText("Where should we begin?");

    const results = await axe(container, {
      rules: {
        "color-contrast": { enabled: false },
      },
    });

    expect(results).toHaveNoViolations();
  });

  it("traps keyboard focus inside the command palette", async () => {
    const user = userEvent.setup();
    render(
      <CommandPalette
        isOpen
        onClose={vi.fn()}
        onRunCommand={vi.fn()}
      />,
    );

    const search = screen.getByPlaceholderText(/search, ask, or run/i);
    await waitFor(() => expect(search).toHaveFocus());

    await user.keyboard("{Shift>}{Tab}{/Shift}");

    expect(screen.getByRole("button", { name: /clear thread/i })).toHaveFocus();
  });

  it("keeps primary rail controls accessible by label", async () => {
    seedApiKey();
    render(
      <App />,
    );

    await screen.findByText("Where should we begin?");

    expect(screen.getByRole("button", { name: /open ask workspace/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /menu and recents/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open account settings/i })).toBeInTheDocument();
  });
});
