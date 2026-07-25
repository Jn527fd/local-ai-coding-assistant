import { describe, expect, it, vi } from "vitest"
import type { Conversation } from "../../domain/models"
import {
  mapBackendConversationToConversation,
  mapConversationToBackendRecord,
} from "./conversationMapper"

describe("conversationMapper", () => {
  it("maps backend settings, metadata, messages, and attachments", () => {
    const conversation = mapBackendConversationToConversation({
      id: "chat-1",
      title: "Mapped chat",
      createdAt: "2026-07-20T10:00:00.000Z",
      updatedAt: "2026-07-20T11:00:00.000Z",
      settings: {
        llmModel: "qwen3:4b",
        embedderModel: "all-minilm",
        ocrEngine: "ocrmypdf",
        pdfParser: "pymupdf",
        chunker: "recursive",
        vectorDatabase: "chroma",
        ragPipeline: "reranked",
        reranker: "bge-reranker-v2:m3",
        contextCompressor: "token",
        visionModel: "llava:7b",
      },
      metadata: {
        proposedFrontend: {
          systemPrompt: "Answer from local context.",
          sourceIds: ["doc-1", "doc-2"],
          temporary: true,
        },
      },
      messages: [
        {
          id: "msg-1",
          role: "assistant",
          content: "Ready.",
          status: "streaming",
          createdAt: "2026-07-20T10:01:00.000Z",
          attachments: [
            {
              id: "att-1",
              filename: "notes.pdf",
              mediaType: "application/pdf",
              size: 1200,
              status: "ready",
            },
          ],
          metadata: {
            ragUsed: true,
            ragWarnings: ["Skipped stale context."],
            rerankingUsed: true,
            rerankerModel: "bge-reranker",
            rerankWarnings: [],
            compressionUsed: true,
            compressorMode: "token",
            compressionWarnings: ["Trimmed history."],
            sources: [
              {
                sourceNumber: 1,
                documentId: "doc-1",
                documentName: "notes.pdf",
                chunkId: "chunk-1",
                chunkIndex: 0,
                score: 0.7,
                vectorScore: 0.7,
                rerankScore: 0.9,
                finalRank: 1,
                textPreview: "Important local context.",
              },
            ],
          },
        },
      ],
    })

    expect(conversation).toMatchObject({
      id: "chat-1",
      title: "Mapped chat",
      createdAt: "2026-07-20T10:00:00.000Z",
      updatedAt: "2026-07-20T11:00:00.000Z",
      systemPrompt: "Answer from local context.",
      sourceIds: ["doc-1", "doc-2"],
      temporary: true,
      modelConfiguration: {
        llmModel: "qwen3:4b",
        embedder: "all-minilm",
        ocrEngine: "ocrmypdf",
        pdfParser: "pymupdf",
        chunker: "recursive",
        vectorDatabase: "chroma",
        ragPipeline: "reranked",
        reranker: "bge-reranker-v2:m3",
        contextCompressor: "token",
        visionModel: "llava:7b",
      },
      messages: [
        {
          id: "msg-1",
          conversationId: "chat-1",
          role: "assistant",
          content: "Ready.",
          status: "streaming",
          attachments: [{ id: "att-1", filename: "notes.pdf" }],
          metadata: {
            ragUsed: true,
            ragWarnings: ["Skipped stale context."],
            rerankingUsed: true,
            rerankerModel: "bge-reranker",
            compressionUsed: true,
            compressorMode: "token",
            compressionWarnings: ["Trimmed history."],
            sources: [
              expect.objectContaining({
                sourceNumber: 1,
                documentName: "notes.pdf",
                vectorScore: 0.7,
                rerankScore: 0.9,
              }),
            ],
          },
        },
      ],
    })
  })

  it("falls back safely for older backend records", () => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date("2026-07-22T12:00:00.000Z"))
    try {
      const conversation = mapBackendConversationToConversation({
        id: "legacy",
        title: "",
        metadata: {
          systemPrompt: "Legacy prompt",
          documentIds: ["doc-a"],
        },
        attachmentReferences: [
          { documentId: "doc-b", name: "ignored when metadata exists" },
        ],
        messages: [
          { role: "user", content: "Keep me" },
          { role: "tool", content: "Drop me" },
          { role: "assistant", content: "" },
        ],
      })

      expect(conversation.title).toBe("Untitled thread")
      expect(conversation.createdAt).toBe("2026-07-22T12:00:00.000Z")
      expect(conversation.updatedAt).toBe("2026-07-22T12:00:00.000Z")
      expect(conversation.systemPrompt).toBe("Legacy prompt")
      expect(conversation.sourceIds).toEqual(["doc-a"])
      expect(conversation.messages).toEqual([
        expect.objectContaining({
          id: "legacy-message-0",
          role: "user",
          content: "Keep me",
          status: "complete",
          attachments: [],
        }),
      ])
      expect(conversation.modelConfiguration).toMatchObject({
        llmModel: "llama3.2:3b",
        visionModel: "llama3.2-vision:11b",
      })
    } finally {
      vi.useRealTimers()
    }
  })

  it("round-trips proposed-only fields into backend metadata", () => {
    const conversation: Conversation = {
      id: "chat-2",
      title: "Round trip",
      createdAt: "2026-07-20T10:00:00.000Z",
      updatedAt: "2026-07-20T11:00:00.000Z",
      systemPrompt: "Preserve this",
      sourceIds: ["doc-1"],
      temporary: false,
      modelConfiguration: {
        llmModel: "qwen3:4b",
        visionModel: "llava:7b",
        embedder: "all-minilm",
        chunker: "recursive",
        ragPipeline: "basic",
      },
      messages: [
        {
          id: "msg-1",
          conversationId: "chat-2",
          role: "user",
          content: "Hello",
          status: "complete",
          createdAt: "2026-07-20T10:01:00.000Z",
          attachments: [
            {
              id: "doc-1",
              filename: "doc.pdf",
              mediaType: "application/pdf",
              size: 10,
              status: "ready",
            },
          ],
          metadata: {
            ragUsed: true,
            sources: [
              {
                sourceNumber: 1,
                documentId: "doc-1",
                documentName: "doc.pdf",
                chunkId: "chunk-1",
                chunkIndex: 0,
                score: 0.5,
                vectorScore: 0.5,
                rerankScore: null,
                finalRank: 1,
                textPreview: "Stored citation.",
              },
            ],
          },
        },
      ],
    }

    expect(mapConversationToBackendRecord(conversation)).toMatchObject({
      id: "chat-2",
      settings: {
        llmModel: "qwen3:4b",
        visionModel: "llava:7b",
        embedderModel: "all-minilm",
        chunker: "recursive",
        ragPipeline: "basic",
      },
      metadata: {
        proposedFrontend: {
          systemPrompt: "Preserve this",
          sourceIds: ["doc-1"],
          temporary: false,
        },
      },
      attachmentReferences: [
        {
          id: "doc-1",
          name: "doc.pdf",
          mediaType: "application/pdf",
          size: 10,
          status: "ready",
        },
      ],
      messages: [
        {
          id: "msg-1",
          content: "Hello",
          metadata: {
            ragUsed: true,
            sources: [
              expect.objectContaining({
                sourceNumber: 1,
                documentName: "doc.pdf",
                textPreview: "Stored citation.",
              }),
            ],
          },
        },
      ],
    })
  })
})
