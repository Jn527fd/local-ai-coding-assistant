import { afterEach, describe, expect, it, vi } from "vitest";

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

async function importApiForTest() {
  vi.resetModules();
  vi.stubGlobal("location", {
    protocol: "http:",
    hostname: "192.168.1.204",
  });

  return import("./api.js");
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api login", () => {
  it("verifies the cookie-backed session before resolving", async () => {
    const calls = [];
    vi.stubGlobal("fetch", async (url, options) => {
      calls.push({ url, options });
      if (url.endsWith("/auth/login")) {
        return jsonResponse({ username: "chuy" });
      }
      if (url.endsWith("/auth/me")) {
        return jsonResponse({ username: "chuy" });
      }
      return jsonResponse({ detail: "Unexpected request." }, 500);
    });

    const { API_BASE_URL, login } = await importApiForTest();
    const session = await login("chuy", "password");

    expect(API_BASE_URL).toBe("http://192.168.1.204:8000");
    expect(session).toEqual({ username: "chuy" });
    expect(calls.map((call) => call.url)).toEqual([
      "http://192.168.1.204:8000/auth/login",
      "http://192.168.1.204:8000/auth/me",
    ]);
    expect(calls[0].options.credentials).toBe("include");
    expect(calls[1].options.credentials).toBe("include");
  });

  it("fails clearly when the session cookie is not usable", async () => {
    vi.stubGlobal("fetch", async (url) => {
      if (url.endsWith("/auth/login")) {
        return jsonResponse({ username: "chuy" });
      }
      if (url.endsWith("/auth/me")) {
        return jsonResponse({ detail: "Login required." }, 401);
      }
      return jsonResponse({ detail: "Unexpected request." }, 500);
    });

    const { login } = await importApiForTest();

    await expect(login("chuy", "password")).rejects.toThrow(
      /browser session cookie could not be verified/,
    );
  });
});

describe("api chat", () => {
  it("sends conversation settings with chat requests", async () => {
    const calls = [];
    vi.stubGlobal("fetch", async (url, options) => {
      calls.push({ url, options });
      return jsonResponse({ model: "qwen3:4b", answer: "ok" });
    });

    const { sendChat } = await importApiForTest();
    await sendChat(
      "test-key",
      "Hello",
      [{ role: "user", content: "Earlier" }],
      {
        llmModel: "llama3.2:3b",
        embedderModel: "nomic-embed-text:latest",
        ocrEngine: "none",
      },
      "chat-1",
      {
        enabled: true,
        topK: 3,
        candidateK: 12,
        documentIds: ["doc-1"],
        includeSources: true,
      },
    );

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe("http://192.168.1.204:8000/chat");
    expect(calls[0].options.headers.Authorization).toBe("Bearer test-key");
    expect(JSON.parse(calls[0].options.body)).toEqual({
      conversationId: "chat-1",
      message: "Hello",
      history: [{ role: "user", content: "Earlier" }],
      conversationSettings: {
        llmModel: "llama3.2:3b",
        embedderModel: "nomic-embed-text:latest",
        ocrEngine: "none",
      },
      ragOptions: {
        enabled: true,
        topK: 3,
        candidateK: 12,
        documentIds: ["doc-1"],
        includeSources: true,
      },
    });
  });
});

describe("api documents", () => {
  it("uploads documents as multipart form data", async () => {
    const calls = [];
    vi.stubGlobal("fetch", async (url, options) => {
      calls.push({ url, options });
      return jsonResponse({
        documentId: "doc-1",
        conversationId: "conversation-a",
        status: "uploaded",
      });
    });

    const { uploadDocument } = await importApiForTest();
    const file = new File(["hello"], "notes.txt", { type: "text/plain" });
    await uploadDocument(
      "test-key",
      "conversation-a",
      file,
      { chunker: "recursive" },
    );

    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe("http://192.168.1.204:8000/documents/upload");
    expect(calls[0].options.headers.Authorization).toBe("Bearer test-key");
    expect(calls[0].options.headers["Content-Type"]).toBeUndefined();
    expect(calls[0].options.body).toBeInstanceOf(FormData);
    expect(calls[0].options.body.get("conversationId")).toBe("conversation-a");
    expect(calls[0].options.body.get("conversationSettings")).toBe(
      JSON.stringify({ chunker: "recursive" }),
    );
    expect(calls[0].options.body.get("file").name).toBe("notes.txt");
  });

  it("processes and lists conversation documents", async () => {
    const calls = [];
    vi.stubGlobal("fetch", async (url, options) => {
      calls.push({ url, options });
      if (url.endsWith("/documents/doc-1/process")) {
        return jsonResponse({
          documentId: "doc-1",
          conversationId: "conversation-a",
          status: "processed",
          chunkCount: 2,
        });
      }
      if (url.includes("/documents?")) {
        return jsonResponse({
          conversationId: "conversation-a",
          documents: [{ documentId: "doc-1", status: "processed" }],
        });
      }
      return jsonResponse({ detail: "Unexpected request." }, 500);
    });

    const { listDocuments, processDocument } = await importApiForTest();
    await processDocument(
      "test-key",
      "doc-1",
      "conversation-a",
      { chunker: "fixed" },
    );
    await listDocuments("test-key", "conversation-a");

    expect(calls[0].url).toBe(
      "http://192.168.1.204:8000/documents/doc-1/process",
    );
    expect(JSON.parse(calls[0].options.body)).toEqual({
      conversationId: "conversation-a",
      conversationSettings: { chunker: "fixed" },
    });
    expect(calls[1].url).toBe(
      "http://192.168.1.204:8000/documents?conversationId=conversation-a",
    );
  });

  it("indexes, searches, lists, and deletes document indexes", async () => {
    const calls = [];
    vi.stubGlobal("fetch", async (url, options) => {
      calls.push({ url, options });
      if (url.endsWith("/documents/doc-1/index")) {
        return jsonResponse({ collectionId: "collection-1", indexedChunks: 2 });
      }
      if (url.endsWith("/documents/search")) {
        return jsonResponse({ results: [{ chunkId: "chunk-1", score: 0.8 }] });
      }
      if (url.includes("/documents/indexes/collection-1")) {
        return jsonResponse({ deleted: true });
      }
      if (url.includes("/documents/indexes?")) {
        return jsonResponse({ indexes: [{ collectionId: "collection-1" }] });
      }
      return jsonResponse({ detail: "Unexpected request." }, 500);
    });

    const {
      deleteDocumentIndex,
      indexDocument,
      listDocumentIndexes,
      searchDocuments,
    } = await importApiForTest();
    await indexDocument(
      "test-key",
      "doc-1",
      "conversation-a",
      { embedderModel: "embed-a" },
    );
    await searchDocuments(
      "test-key",
      "conversation-a",
      "banana",
      { embedderModel: "embed-a" },
      { documentIds: ["doc-1"], topK: 3 },
    );
    await listDocumentIndexes("test-key", "conversation-a");
    await deleteDocumentIndex("test-key", "collection-1", "conversation-a");

    expect(calls[0].url).toBe(
      "http://192.168.1.204:8000/documents/doc-1/index",
    );
    expect(JSON.parse(calls[0].options.body)).toEqual({
      conversationId: "conversation-a",
      conversationSettings: { embedderModel: "embed-a" },
    });
    expect(calls[1].url).toBe("http://192.168.1.204:8000/documents/search");
    expect(JSON.parse(calls[1].options.body)).toEqual({
      conversationId: "conversation-a",
      query: "banana",
      conversationSettings: { embedderModel: "embed-a" },
      documentIds: ["doc-1"],
      topK: 3,
    });
    expect(calls[2].url).toBe(
      "http://192.168.1.204:8000/documents/indexes?conversationId=conversation-a",
    );
    expect(calls[3].url).toBe(
      "http://192.168.1.204:8000/documents/indexes/collection-1?conversationId=conversation-a",
    );
    expect(calls[3].options.method).toBe("DELETE");
  });
});
