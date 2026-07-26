import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { ChatTranscript } from "./ChatTranscript"
import type { Conversation } from "../../domain/models"

const baseConversation: Conversation = {
  id: "conversation-1",
  title: "Status test",
  createdAt: "2026-07-18T12:00:00Z",
  updatedAt: "2026-07-18T12:00:00Z",
  messages: [],
  systemPrompt: "",
  modelConfiguration: { llmModel: "llm", visionModel: "vision" },
  sourceIds: [],
  temporary: false,
}

describe("ChatTranscript", () => {
  it.each([
    ["pending", "Waiting for response"],
    ["streaming", "Responding"],
    ["failed", "Generation failed"],
  ] as const)("renders the %s message state", (status, expected) => {
    render(
      <ChatTranscript
        activeConversation={{
          ...baseConversation,
          messages: [
            {
              id: "message-1",
              conversationId: baseConversation.id,
              role: "assistant",
              content: status === "streaming" ? "Partial" : "",
              status,
              createdAt: baseConversation.createdAt,
              attachments: [],
              error: status === "failed" ? "Generation failed" : undefined,
            },
          ],
        }}
        tempChat={false}
        showMessageTimestamps={true}
        onCancelMessage={vi.fn()}
        onRetryMessage={vi.fn()}
        onRegenerateMessage={vi.fn()}
      />,
    )
    expect(screen.getByRole("status")).toHaveTextContent(expected)
  })

  it("renders completed content and regeneration", () => {
    render(
      <ChatTranscript
        activeConversation={{
          ...baseConversation,
          messages: [
            {
              id: "message-1",
              conversationId: baseConversation.id,
              role: "assistant",
              content: "Completed response",
              status: "complete",
              createdAt: baseConversation.createdAt,
              attachments: [],
            },
          ],
        }}
        tempChat={false}
        showMessageTimestamps={true}
        onCancelMessage={vi.fn()}
        onRetryMessage={vi.fn()}
        onRegenerateMessage={vi.fn()}
      />,
    )
    expect(screen.getByText("Completed response")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Regenerate" })).toBeEnabled()
  })

  it("shows timestamps when the setting is enabled", () => {
    render(
      <ChatTranscript
        activeConversation={{
          ...baseConversation,
          messages: [
            {
              id: "message-1",
              conversationId: baseConversation.id,
              role: "assistant",
              content: "Message with time",
              status: "complete",
              createdAt: baseConversation.createdAt,
              attachments: [],
            },
          ],
        }}
        tempChat={false}
        showMessageTimestamps={true}
        onCancelMessage={vi.fn()}
        onRetryMessage={vi.fn()}
        onRegenerateMessage={vi.fn()}
      />,
    )

    const expectedTime = new Date(
      baseConversation.createdAt,
    ).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })
    expect(screen.getByText(expectedTime)).toBeInTheDocument()
  })

  it("keeps response metadata out of the simple transcript view", () => {
    render(
      <ChatTranscript
        activeConversation={{
          ...baseConversation,
          messages: [
            {
              id: "message-1",
              conversationId: baseConversation.id,
              role: "assistant",
              content: "Answer grounded in sources.",
              status: "complete",
              createdAt: baseConversation.createdAt,
              attachments: [],
              metadata: {
                ragUsed: true,
                ragWarnings: ["Skipped one stale source."],
                rerankingUsed: true,
                rerankerModel: "bge-reranker",
                rerankWarnings: ["Reranker warning."],
                compressionUsed: true,
                compressorMode: "token",
                compressionWarnings: ["Trimmed older history."],
                sources: [
                  {
                    sourceNumber: 1,
                    documentId: "doc-a",
                    documentName: "notes.pdf",
                    chunkId: "chunk-a",
                    chunkIndex: 0,
                    score: 0.72,
                    vectorScore: 0.72,
                    rerankScore: 0.91,
                    finalRank: 1,
                    textPreview: "A relevant passage from the document.",
                    pageNumber: 3,
                    collectionId: "collection-a",
                  },
                ],
              },
            },
          ],
        }}
        tempChat={false}
        showMessageTimestamps={true}
        onCancelMessage={vi.fn()}
        onRetryMessage={vi.fn()}
        onRegenerateMessage={vi.fn()}
      />,
    )

    expect(screen.getByText("Answer grounded in sources.")).toBeInTheDocument()
    expect(
      screen.queryByLabelText("Response source and context metadata"),
    ).not.toBeInTheDocument()
    expect(screen.queryByText("[1] notes.pdf")).not.toBeInTheDocument()
    expect(screen.queryByText("Reranked with bge-reranker")).not.toBeInTheDocument()
    expect(screen.queryByText("Context compressed (token)")).not.toBeInTheDocument()
    expect(screen.queryByText("Skipped one stale source.")).not.toBeInTheDocument()
  })
})
