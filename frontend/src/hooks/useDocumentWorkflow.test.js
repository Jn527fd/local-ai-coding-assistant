import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  getJob,
  listDocumentIndexes,
  listDocuments,
  searchDocuments,
  startIndexDocumentJob,
  startProcessDocumentJob,
  uploadDocument,
} from "../api.js";
import { buildDefaultConversationSettings } from "../chatState.js";
import { useDocumentWorkflow } from "./useDocumentWorkflow.js";

vi.mock("../api.js", () => ({
  getJob: vi.fn(),
  listDocumentIndexes: vi.fn(),
  listDocuments: vi.fn(),
  searchDocuments: vi.fn(),
  startIndexDocumentJob: vi.fn(),
  startProcessDocumentJob: vi.fn(),
  uploadDocument: vi.fn(),
}));

function renderDocumentWorkflow({ activeChat, apiKey = "test-key" } = {}) {
  return renderHook(() =>
    useDocumentWorkflow({
      activeChat,
      apiKey,
      authState: "authenticated",
      defaultConversationSettings: buildDefaultConversationSettings(),
      showToast: vi.fn(),
    }),
  );
}

describe("useDocumentWorkflow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDocuments.mockResolvedValue({ documents: [] });
    listDocumentIndexes.mockResolvedValue({ indexes: [] });
  });

  it("loads documents and indexes for the active chat", async () => {
    listDocuments.mockResolvedValueOnce({
      documents: [{ documentId: "doc-a", originalFilename: "notes.txt" }],
    });
    listDocumentIndexes.mockResolvedValueOnce({
      indexes: [{ collectionId: "json-a" }],
    });

    const { result } = renderDocumentWorkflow({
      activeChat: { id: "chat-a", settings: {}, messages: [] },
    });

    await waitFor(() => {
      expect(result.current.activeDocuments).toHaveLength(1);
    });
    expect(result.current.activeDocumentIndexes).toHaveLength(1);
    expect(listDocuments).toHaveBeenCalledWith("test-key", "chat-a");
    expect(listDocumentIndexes).toHaveBeenCalledWith("test-key", "chat-a");
  });

  it("uploads and processes a supported document", async () => {
    uploadDocument.mockResolvedValueOnce({
      documentId: "doc-a",
      originalFilename: "notes.txt",
    });
    startProcessDocumentJob.mockResolvedValueOnce({ job: { id: "job-a" } });
    getJob.mockResolvedValueOnce({
      job: {
        id: "job-a",
        state: "succeeded",
        progress: 100,
        result: {
          status: "processed",
          chunkCount: 2,
          document: {
            documentId: "doc-a",
            originalFilename: "notes.txt",
            status: "processed",
          },
        },
      },
    });
    startIndexDocumentJob.mockResolvedValueOnce({ job: { id: "job-index" } });
    getJob.mockResolvedValueOnce({
      job: {
        id: "job-index",
        state: "succeeded",
        progress: 100,
        result: { indexedChunks: 2 },
      },
    });
    const { result } = renderDocumentWorkflow({
      activeChat: { id: "chat-a", settings: {}, messages: [] },
    });

    let uploaded;
    await act(async () => {
      uploaded = await result.current.handleUploadDocument(
        new File(["hello"], "notes.txt", { type: "text/plain" }),
      );
    });

    expect(uploaded).toBe(true);
    expect(uploadDocument).toHaveBeenCalled();
    expect(startProcessDocumentJob).toHaveBeenCalledWith(
      "test-key",
      "doc-a",
      "chat-a",
      expect.any(Object),
    );
    expect(startIndexDocumentJob).toHaveBeenCalledWith(
      "test-key",
      "doc-a",
      "chat-a",
      expect.any(Object),
    );
    expect(result.current.documentBusy).toBe(false);
    expect(result.current.documentJobProgress).toBeNull();
  });

  it("rejects unsupported document extensions before calling the API", async () => {
    const { result } = renderDocumentWorkflow({
      activeChat: { id: "chat-a", settings: {}, messages: [] },
    });

    let uploaded;
    await act(async () => {
      uploaded = await result.current.handleUploadDocument(
        new File(["hello"], "notes.exe"),
      );
    });

    expect(uploaded).toBe(false);
    expect(result.current.documentError).toMatch(/only \.txt/i);
    expect(uploadDocument).not.toHaveBeenCalled();
  });

  it("searches indexed documents and preserves warnings", async () => {
    searchDocuments.mockResolvedValueOnce({
      results: [{ chunkId: "chunk-a", text: "answer" }],
      warnings: ["low confidence"],
    });
    const { result } = renderDocumentWorkflow({
      activeChat: { id: "chat-a", settings: {}, messages: [] },
    });

    act(() => {
      result.current.setDocumentSearchQuery("answer");
    });
    let searched;
    await act(async () => {
      searched = await result.current.handleSearchDocuments();
    });

    expect(searched).toBe(true);
    expect(result.current.documentSearchResults).toHaveLength(1);
    expect(result.current.documentSearchWarnings).toEqual(["low confidence"]);
  });

  it("indexes processed documents through the job API", async () => {
    startIndexDocumentJob.mockResolvedValueOnce({ job: { id: "job-index" } });
    getJob.mockResolvedValueOnce({
      job: {
        id: "job-index",
        state: "succeeded",
        progress: 100,
        result: { indexedChunks: 3 },
      },
    });
    const { result } = renderDocumentWorkflow({
      activeChat: { id: "chat-a", settings: {}, messages: [] },
    });

    let indexed;
    await act(async () => {
      indexed = await result.current.handleIndexDocument({
        documentId: "doc-a",
        originalFilename: "notes.txt",
        status: "processed",
      });
    });

    expect(indexed).toBe(true);
    expect(startIndexDocumentJob).toHaveBeenCalledWith(
      "test-key",
      "doc-a",
      "chat-a",
      expect.any(Object),
    );
    expect(result.current.indexingDocumentId).toBe("");
  });
});
