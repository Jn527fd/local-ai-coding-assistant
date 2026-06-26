import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import AccountPanel from "../AccountPanel.jsx";
import CommandPalette from "../CommandPalette.jsx";
import Composer from "../Composer.jsx";
import NavigationRail from "../NavigationRail.jsx";
import Workspace from "../Workspace.jsx";

const baseChat = {
  id: "chat-1",
  title: "Architecture thread",
  messages: [],
  updatedAt: "2026-06-25T12:00:00.000Z",
};

const modelStatus = {
  active_model: "qwen3:4b",
  supported_models: [
    {
      name: "qwen3:4b",
      label: "qwen3:4b",
      parameter_size: "4B",
      size_display: "2.4 GiB",
      quantization_level: "Q4_K_M",
    },
  ],
  ollama_connected: true,
  phase: "idle",
  progress: null,
  message: "Ready",
  error: null,
  warning: null,
};

function WorkspaceHarness({
  activeChat = baseChat,
  activeModel = "qwen3:4b",
  apiStatus = { status: "online", message: "FastAPI is online" },
  error = "",
  hasIndexedRepository = false,
  indexedRepository = null,
  isSending = false,
  notice = "",
  onDeleteChat = vi.fn(),
  onExportChat = vi.fn(),
  onIndexRepository = vi.fn(),
  onOpenModelSettings = vi.fn(),
  onOpenSourceDetails = vi.fn(),
  onRenameChat = vi.fn(),
  onSendMessage = vi.fn(),
} = {}) {
  const [message, setMessage] = React.useState("");
  const composerRef = React.useRef(null);

  function handlePrompt(prompt) {
    setMessage(prompt);
    window.requestAnimationFrame(() => composerRef.current?.focus());
  }

  return (
    <>
      <Workspace
        activeChat={activeChat}
        apiStatus={apiStatus}
        error={error}
        hasIndexedRepository={hasIndexedRepository}
        indexedRepository={indexedRepository}
        isSending={isSending}
        modelStatus={modelStatus}
        notice={notice}
        onDeleteChat={onDeleteChat}
        onExportChat={onExportChat}
        onIndexRepository={onIndexRepository}
        onOpenModelSettings={onOpenModelSettings}
        onOpenSourceDetails={onOpenSourceDetails}
        onPrompt={handlePrompt}
        onRenameChat={onRenameChat}
        onSendMessage={onSendMessage}
      />
      <Composer
        activeChat={activeChat}
        activeModel={activeModel}
        composerRef={composerRef}
        indexedRepository={indexedRepository}
        isSending={isSending}
        message={message}
        onIndexRepository={onIndexRepository}
        onMessageChange={setMessage}
        onOpenModelSettings={onOpenModelSettings}
        onSendMessage={onSendMessage}
      />
    </>
  );
}

describe("NavigationRail", () => {
  it("renders an icon rail and toggles the recents drawer", async () => {
    const user = userEvent.setup();
    const onNewChat = vi.fn();
    const onSelectSection = vi.fn();
    const onRenameChat = vi.fn();
    const onDeleteChat = vi.fn();
    const onCloseDrawer = vi.fn();
    const onToggleDrawer = vi.fn();

    render(
      <NavigationRail
        activeChatId="chat-1"
        chats={[baseChat]}
        currentSection="ask"
        drawerOpen
        isFastApiOnline
        isOllamaOnline
        memoryUsage="1/5 chats"
        onCloseDrawer={onCloseDrawer}
        onDeleteChat={onDeleteChat}
        onNewChat={onNewChat}
        onOpenSettings={vi.fn()}
        onRenameChat={onRenameChat}
        onSelectChat={vi.fn()}
        onSelectSection={onSelectSection}
        onToggleDrawer={onToggleDrawer}
        username="chuy"
      />,
    );

    await user.click(screen.getByRole("button", { name: /^new chat\. 1 of 5 used$/i }));
    await user.click(screen.getByRole("button", { name: /menu and recents/i }));
    await user.click(screen.getByRole("button", { name: /rename architecture thread/i }));
    await user.click(screen.getByRole("button", { name: /close recents/i }));

    expect(onNewChat).toHaveBeenCalledTimes(1);
    expect(onToggleDrawer).toHaveBeenCalledTimes(1);
    expect(onRenameChat).toHaveBeenCalledWith("chat-1");
    expect(onCloseDrawer).toHaveBeenCalled();
    expect(screen.getByText("Architecture thread")).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/search chats/i)).toBeInTheDocument();
    expect(screen.getByText("Previous 7 Days")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^settings$/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /pin navigation/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /collapse navigation/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Models")).not.toBeInTheDocument();
  });
});

describe("Workspace / Conversation / Composer", () => {
  it("renders the no-repository onboarding state and composer controls", () => {
    render(
      <WorkspaceHarness />,
    );

    expect(screen.getByText("Where should we begin?")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /index repository/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /configure models/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /drop a local folder here/i })).not.toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: /ask about your codebase/i })).toHaveAttribute(
      "placeholder",
      "Ask anything",
    );
    expect(screen.getByRole("button", { name: /open composer model selector/i })).toBeInTheDocument();
    expect(screen.queryByText(/No repository/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /explain this repository/i })).not.toBeInTheDocument();
    expect(screen.queryByText("0 files")).not.toBeInTheDocument();
  });

  it("renders a repository-ready empty state with summary and prompt shortcuts", async () => {
    const user = userEvent.setup();

    render(
      <WorkspaceHarness
        hasIndexedRepository
        indexedRepository={{
          name: "local-ai-coding-assistant",
          indexedFiles: 42,
          languages: ["Python", "JavaScript"],
          lastIndexedAt: "2026-06-25 12:00",
        }}
      />,
    );

    expect(screen.getByText("Repository ready")).toBeInTheDocument();
    expect(
      screen.getByText("local-ai-coding-assistant is indexed and ready."),
    ).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Python, JavaScript")).toBeInTheDocument();
    expect(screen.getByText("2026-06-25 12:00")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /trace the auth flow/i }));

    expect(screen.getByRole("textbox", { name: /ask about your codebase/i })).toHaveValue(
      "Trace the auth flow in local-ai-coding-assistant",
    );
  });

  it("submits with Ctrl+Enter and opens source details from citations", async () => {
    const user = userEvent.setup();
    const onSendMessage = vi.fn().mockResolvedValue(true);
    const onOpenSourceDetails = vi.fn();

    render(
      <WorkspaceHarness
        activeChat={{
          ...baseChat,
          messages: [
            { role: "user", content: "Where is chat handled?" },
            {
              role: "assistant",
              content: "The chat route is in the backend router.",
              sources: ["backend/app/routers/chat.py"],
            },
          ],
        }}
        hasIndexedRepository
        indexedRepository={{ name: "local-ai-coding-assistant" }}
        onOpenSourceDetails={onOpenSourceDetails}
        onSendMessage={onSendMessage}
      />,
    );

    await user.click(screen.getByRole("button", { name: /open source backend\/app\/routers\/chat.py/i }));
    await user.type(screen.getByRole("textbox"), "Add tests");
    await user.keyboard("{Control>}{Enter}{/Control}");

    expect(onOpenSourceDetails).toHaveBeenCalledWith("backend/app/routers/chat.py");
    expect(onSendMessage).toHaveBeenCalledWith("Add tests");
  });

  it("autocompletes slash commands from the composer", async () => {
    const user = userEvent.setup();

    render(<WorkspaceHarness />);

    await user.type(screen.getByRole("textbox", { name: /ask about your codebase/i }), "/te");

    expect(screen.getByRole("listbox", { name: /slash commands/i })).toBeInTheDocument();

    await user.keyboard("{Enter}");

    expect(screen.getByRole("textbox", { name: /ask about your codebase/i })).toHaveValue(
      "/tests Generate tests for the selected flow",
    );
  });
});

describe("CommandPalette", () => {
  it("filters and runs developer commands", async () => {
    const user = userEvent.setup();
    const onRunCommand = vi.fn();

    render(
      <CommandPalette
        isOpen
        onClose={vi.fn()}
        onRunCommand={onRunCommand}
      />,
    );

    await user.type(screen.getByPlaceholderText(/search, ask, or run/i), "model");
    await user.click(screen.getByRole("button", { name: /switch model/i }));

    expect(screen.queryByText("Clear thread")).not.toBeInTheDocument();
    expect(onRunCommand).toHaveBeenCalledWith("switch-model");
  });
});

describe("ModelSelector", () => {
  it("loads mocked Ollama models in account settings", async () => {
    render(
      <AccountPanel
        apiKey="test-key"
        isOpen
        onApiKeyChange={vi.fn()}
        onClose={vi.fn()}
        onLogout={vi.fn()}
        onModelStatus={vi.fn()}
        username="test-user"
      />,
    );

    await waitFor(() => {
      expect(screen.getByRole("combobox", { name: /model catalog/i })).toHaveValue(
        "qwen3:4b",
      );
    });
    expect(screen.getByText(/llama3.2:3b/i)).toBeInTheDocument();
    expect(screen.getByText("Ollama connected")).toBeInTheDocument();
  });
});
