import { afterEach, describe, expect, it, vi } from "vitest"
import type { ApiClient, ApiRequestOptions } from "../../api"
import { createDefaultConversationDraft } from "../../domain/defaults"
import type { ApiKeyStorage } from "../apiKeyStorage"
import { AppError } from "../errors"
import { createHttpServices } from "./createHttpServices"

interface ApiCall {
  path: string
  options: ApiRequestOptions
}

interface FetchCall {
  url: string
  init?: RequestInit
}

function createFakeApiClient(
  handler: (path: string, options: ApiRequestOptions) => unknown,
): ApiClient {
  return {
    async request<Response,>(
      path: string,
      options: ApiRequestOptions = {},
    ): Promise<Response> {
      return handler(path, options) as Response
    },
  }
}

describe("HTTP application services", () => {
  const createMemoryStorage = (initial = ""): ApiKeyStorage & {
    value: string
  } => ({
    value: initial,
    get() {
      return this.value
    },
    set(apiKey) {
      this.value = apiKey
    },
  })

  it("maps sign in to the current backend login endpoint", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        return { username: "naran" }
      }),
    })

    await expect(
      services.auth.signIn({ username: "naran", password: "secret" }),
    ).resolves.toMatchObject({
      accessToken: "",
      user: {
        id: "local-naran",
        username: "naran",
        email: "naran@local.invalid",
        displayName: "naran",
      },
    })
    expect(calls).toEqual([
      {
        path: "/auth/login",
        options: {
          method: "POST",
          body: { username: "naran", password: "secret" },
        },
      },
    ])
  })

  it("restores a cookie-backed backend session", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient((path) => {
        expect(path).toBe("/auth/me")
        return { username: "local-user" }
      }),
    })

    await expect(services.auth.restoreSession()).resolves.toMatchObject({
      accessToken: "",
      user: { username: "local-user" },
    })
  })

  it("treats unauthorized session restore as unauthenticated", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient(() => {
        throw new AppError("Sign in to continue.", {
          code: "unauthorized",
          status: 401,
        })
      }),
    })

    await expect(services.auth.restoreSession()).resolves.toBeNull()
  })

  it("maps sign out to the current backend logout endpoint", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        return undefined
      }),
    })

    await expect(services.auth.signOut()).resolves.toBeUndefined()
    expect(calls).toEqual([
      { path: "/auth/logout", options: { method: "POST" } },
    ])
  })

  it("keeps signup and OAuth operations explicitly deferred", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient(() => {
        throw new Error("Unexpected request")
      }),
    })

    await expect(
      services.auth.requestEmailVerification("test@example.com"),
    ).rejects.toMatchObject({ status: 501 })
    await expect(
      services.auth.getOAuthRedirect("google", "/chat"),
    ).rejects.toMatchObject({ status: 501 })
  })

  it("checks account status with the stored bearer API key", async () => {
    const calls: ApiCall[] = []
    const storage = createMemoryStorage("local-secret")
    const services = createHttpServices({
      apiKeyStorage: storage,
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        return {
          username: "naran",
          api_key_configured: true,
          api_key_active: true,
        }
      }),
    })

    await expect(services.account.getStatus()).resolves.toEqual({
      username: "naran",
      apiKeyConfigured: true,
      apiKeyActive: true,
    })
    expect(calls).toEqual([
      {
        path: "/account/status",
        options: { headers: { Authorization: "Bearer local-secret" } },
      },
    ])
  })

  it("updates the backend API key and stores it locally", async () => {
    const calls: ApiCall[] = []
    const storage = createMemoryStorage()
    const services = createHttpServices({
      apiKeyStorage: storage,
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        return {
          username: "naran",
          api_key_configured: true,
          api_key_active: true,
        }
      }),
    })

    await expect(services.account.updateApiKey("new-secret")).resolves.toEqual({
      username: "naran",
      apiKeyConfigured: true,
      apiKeyActive: true,
    })
    expect(storage.value).toBe("new-secret")
    expect(calls).toEqual([
      {
        path: "/account/api-key",
        options: {
          method: "PUT",
          body: { apiKey: "new-secret" },
        },
      },
    ])
  })

  it("loads an honest HTTP profile from backend account status and local preferences", async () => {
    localStorage.setItem(
      "localchat.http-profile.v1",
      JSON.stringify({
        displayName: "Local Display",
        handle: "local.display",
        preferredName: "Local",
        role: "Research",
        about: "Local-only notes",
        preferredLanguage: "en-US",
        responsePreference: "detailed",
      }),
    )
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiKeyStorage: createMemoryStorage("profile-key"),
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/auth/me") return { username: "naran" }
        if (path === "/account/status") {
          return {
            username: "naran",
            api_key_configured: true,
            api_key_active: true,
          }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(services.profile.load()).resolves.toMatchObject({
      profile: {
        id: "local-naran",
        displayName: "Local Display",
        handle: "local.display",
        role: "Research",
        about: "Local-only notes",
        responsePreference: "detailed",
        avatarUrl: null,
        storageLocation:
          "Backend account with browser-local profile preferences",
      },
    })
    expect(services.profile.capabilities).toEqual({
      avatarUpload: false,
      persistence: "local",
    })
    expect(calls).toEqual([
      { path: "/auth/me", options: {} },
      {
        path: "/account/status",
        options: { headers: { Authorization: "Bearer profile-key" } },
      },
    ])
  })

  it("stores HTTP profile edits locally and exports redacted support context", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient((path) => {
        if (path === "/auth/me") return { username: "local-user" }
        if (path === "/account/status") {
          return {
            username: "local-user",
            api_key_configured: false,
            api_key_active: false,
          }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(
      services.profile.update({
        displayName: "Updated User",
        handle: "updated.user",
        preferredName: "Updated",
        role: "Engineering",
        about: "Browser local",
        preferredLanguage: "en-US",
        responsePreference: "concise",
      }),
    ).resolves.toMatchObject({
      profile: {
        displayName: "Updated User",
        handle: "updated.user",
        storageLocation: "Browser-local profile preferences",
      },
    })

    await expect(services.profile.load()).resolves.toMatchObject({
      profile: {
        displayName: "Updated User",
        role: "Engineering",
        responsePreference: "concise",
      },
    })
    await expect(
      services.profile.uploadAvatar(new File(["x"], "avatar.png")),
    ).rejects.toMatchObject({ status: 501 })
    const exported = await services.profile.exportData()
    expect(exported.filename).toBe("localchat-profile.json")
    expect(JSON.parse(exported.content)).toMatchObject({
      support: {
        profilePreferences: "browser-local",
        avatarUpload: "unsupported",
        accountStatus: "backend",
      },
    })
  })

  it("loads component capabilities from the backend", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        return {
          llmModels: [
            {
              id: "qwen3:4b",
              label: "qwen3:4b",
              type: "llmModel",
              available: true,
              source: "ollama",
              name: "qwen3:4b",
            },
          ],
          embedderModels: [
            {
              id: "all-minilm",
              label: "all-minilm",
              type: "embedderModel",
              available: true,
              source: "ollama",
            },
          ],
        }
      }),
    })

    await expect(services.capabilities.list()).resolves.toMatchObject({
      llmModels: [{ id: "qwen3:4b", source: "ollama" }],
      embedderModels: [{ id: "all-minilm" }],
      ocrEngines: [],
      pdfParsers: [],
    })
    expect(calls).toEqual([
      {
        path: "/components/capabilities",
        options: {},
      },
    ])
  })

  it("maps repository HTTP endpoints", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/repos/index-local") {
          return {
            repo_name: "sample-repo",
            indexed_files: 2,
            indexed_chunks: 4,
            freshness: { fresh: true, warnings: [] },
            warnings: [],
          }
        }
        if (path === "/repos/index-local/vector") {
          return {
            repo_name: "sample-repo",
            indexed_files: 2,
            indexed_chunks: 4,
            embedded_chunks: 4,
            conversationId: "chat-a",
            collectionId: "repo-123",
            embedderModel: "all-minilm",
            vectorDatabase: "chroma",
            freshness: {
              fresh: false,
              warnings: ["Repository index is stale."],
            },
            warnings: ["Repository index is stale."],
          }
        }
        if (path === "/repos/ask") {
          return {
            answer: "Repository answer",
            sources: ["src/app.py"],
            warnings: ["Repository index is stale."],
            freshness: {
              fresh: false,
              warnings: ["Repository index is stale."],
            },
          }
        }
        if (path === "/repos/search-vector") {
          return {
            query: "banana",
            warnings: [],
            results: [
              {
                score: 0.9,
                repoName: "sample-repo",
                filePath: "src/app.py",
                startLine: 1,
                endLine: 3,
                language: "python",
                symbolName: "BananaRouter",
                symbolKind: "class",
                text: "class BananaRouter",
              },
            ],
          }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(services.repositories.indexLocal("/repo")).resolves.toEqual({
      repoName: "sample-repo",
      indexedFiles: 2,
      indexedChunks: 4,
      freshness: { fresh: true, warnings: [] },
      warnings: [],
    })
    await expect(
      services.repositories.indexVector({
        path: "/repo",
        conversationId: "chat-a",
        conversationSettings: { embedderModel: "all-minilm" },
      }),
    ).resolves.toMatchObject({
      repoName: "sample-repo",
      embeddedChunks: 4,
      collectionId: "repo-123",
      warnings: ["Repository index is stale."],
    })
    await expect(
      services.repositories.ask({
        repoName: "sample-repo",
        question: "Where is routing?",
      }),
    ).resolves.toMatchObject({
      answer: "Repository answer",
      sources: ["src/app.py"],
      warnings: ["Repository index is stale."],
    })
    await expect(
      services.repositories.searchVector({
        conversationId: "chat-a",
        query: "banana",
        repoName: "sample-repo",
      }),
    ).resolves.toMatchObject({
      results: [
        {
          score: 0.9,
          filePath: "src/app.py",
          symbolName: "BananaRouter",
        },
      ],
    })
    expect(calls.map((call) => [call.path, call.options.method])).toEqual([
      ["/repos/index-local", "POST"],
      ["/repos/index-local/vector", "POST"],
      ["/repos/ask", "POST"],
      ["/repos/search-vector", "POST"],
    ])
    expect(
      calls.find((call) => call.path === "/repos/ask")?.options.body,
    ).toEqual({ repoName: "sample-repo", question: "Where is routing?" })
  })

  it("maps diagnostics HTTP endpoints and support bundle exports", async () => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date("2026-07-25T10:00:00.000Z"))
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/diagnostics/status") {
          return {
            runtime: { status: "ok" },
            models: { ollamaReachable: true },
            documents: { total: 2 },
            retrieval: { vectorDatabase: "json" },
            jobs: { running: 0 },
            warnings: [],
          }
        }
        if (path === "/diagnostics/support-bundle") {
          return {
            redacted: true,
            diagnostics: { runtime: { status: "ok" } },
          }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(services.diagnostics.getStatus()).resolves.toMatchObject({
      runtime: { status: "ok" },
      jobs: { running: 0 },
    })
    await expect(services.diagnostics.exportSupportBundle()).resolves.toEqual({
      filename: "localchat-support-bundle-2026-07-25.json",
      mediaType: "application/json",
      content: JSON.stringify(
        {
          redacted: true,
          diagnostics: { runtime: { status: "ok" } },
        },
        null,
        2,
      ),
    })
    expect(calls.map((call) => call.path)).toEqual([
      "/diagnostics/status",
      "/diagnostics/support-bundle",
    ])
  })

  it("lists and reads backend persisted conversations", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient((path) => {
        if (path === "/conversations") {
          return {
            conversations: [
              backendConversation({
                id: "chat-a",
                title: "Alpha",
                updatedAt: "2026-07-20T12:00:00.000Z",
              }),
              backendConversation({
                id: "chat-b",
                title: "Beta",
                updatedAt: "2026-07-21T12:00:00.000Z",
              }),
            ],
          }
        }
        if (path === "/conversations/chat-a") {
          return {
            conversation: backendConversation({
              id: "chat-a",
              title: "Alpha",
              settings: { llmModel: "qwen3:4b", embedderModel: "all-minilm" },
              metadata: {
                frontend: {
                  systemPrompt: "Be precise.",
                  sourceIds: ["source-1"],
                },
              },
            }),
          }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(services.conversations.list({ limit: 1 })).resolves.toEqual({
      items: [
        {
          id: "chat-b",
          title: "Beta",
          createdAt: "2026-07-21T12:00:00.000Z",
          updatedAt: "2026-07-21T12:00:00.000Z",
          temporary: false,
        },
      ],
      nextCursor: "1",
      total: 2,
    })
    await expect(services.conversations.get("chat-a")).resolves.toMatchObject({
      id: "chat-a",
      title: "Alpha",
      systemPrompt: "Be precise.",
      sourceIds: ["source-1"],
      modelConfiguration: {
        llmModel: "qwen3:4b",
        embedder: "all-minilm",
      },
      messages: [{ role: "user", content: "Hello" }],
    })
  })

  it("creates and deletes backend persisted conversations", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations" && options.method === "POST") {
          return { conversation: options.body }
        }
        if (
          path === "/conversations/conversation-created" &&
          options.method === "DELETE"
        ) {
          return { deleted: true, conversationId: "conversation-created" }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    const created = await services.conversations.create({
      title: "Created",
      ...createDefaultConversationDraft(),
    })
    created.id = "conversation-created"
    await services.conversations.delete(created.id)

    expect(calls[0]).toMatchObject({
      path: "/conversations",
      options: { method: "POST" },
    })
    expect(calls[0].options.body).toMatchObject({
      title: "Created",
      metadata: {
        frontend: {
          systemPrompt: "",
          sourceIds: [],
          temporary: false,
        },
      },
    })
    expect(calls[1]).toEqual({
      path: "/conversations/conversation-created",
      options: { method: "DELETE" },
    })
  })

  it("deletes uploaded sources through the active backend conversation", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return {
            conversation: backendConversation({
              id: "chat-a",
              title: "Chat A",
            }),
          }
        }
        if (
          path === "/documents/doc-a?conversationId=chat-a" &&
          options.method === "DELETE"
        ) {
          return { deleted: true, documentId: "doc-a", conversationId: "chat-a" }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.conversations.get("chat-a")
    await services.sources.delete("doc-a")

    expect(calls.at(-1)).toEqual({
      path: "/documents/doc-a?conversationId=chat-a",
      options: { method: "DELETE" },
    })
  })

  it("keeps temporary conversations local in HTTP mode", async () => {
    const calls: string[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path) => {
        calls.push(path)
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    const created = await services.conversations.create({
      title: "Temporary",
      ...createDefaultConversationDraft(),
      temporary: true,
    })

    await expect(services.conversations.get(created.id)).resolves.toMatchObject(
      {
        id: created.id,
        title: "Temporary",
        temporary: true,
      },
    )
    await expect(
      services.conversations.delete(created.id),
    ).resolves.toBeUndefined()
    expect(calls).toEqual([])
  })

  it("renames backend conversations with update semantics", async () => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date("2026-07-24T10:00:00.000Z"))
    const calls: ApiCall[] = []
    const services = createHttpServices({
      jobPollIntervalMs: 0,
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return {
            conversation: backendConversation({
              id: "chat-a",
              title: "Before",
              metadata: {
                source: "existing",
                frontend: { systemPrompt: "Keep prompt" },
              },
            }),
          }
        }
        if (path === "/conversations/chat-a" && options.method === "PUT") {
          return { conversation: options.body }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(
      services.conversations.rename("chat-a", "After"),
    ).resolves.toMatchObject({
      id: "chat-a",
      title: "After",
      updatedAt: "2026-07-24T10:00:00.000Z",
    })
    expect(calls.at(-1)).toMatchObject({
      path: "/conversations/chat-a",
      options: { method: "PUT" },
    })
    expect(calls.at(-1)?.options.body).toMatchObject({
      id: "chat-a",
      title: "After",
      metadata: {
        source: "existing",
        frontend: { systemPrompt: "Keep prompt" },
      },
    })
  })

  it("persists configuration changes without leaking them to other chats", async () => {
    vi.useFakeTimers({ toFake: ["Date"] })
    vi.setSystemTime(new Date("2026-07-24T11:00:00.000Z"))
    const records = new Map([
      [
        "chat-a",
        backendConversation({
          id: "chat-a",
          title: "First",
          settings: { llmModel: "qwen3:4b", embedderModel: "all-minilm" },
          metadata: {
            frontend: {
              systemPrompt: "First prompt",
              sourceIds: ["doc-a"],
            },
          },
        }),
      ],
      [
        "chat-b",
        backendConversation({
          id: "chat-b",
          title: "Second",
          settings: { llmModel: "llama3.2:3b" },
          metadata: {
            frontend: {
              systemPrompt: "Second prompt",
              sourceIds: [],
            },
          },
        }),
      ],
    ])
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        const id = path.split("/").at(-1) ?? ""
        if (path.startsWith("/conversations/") && !options.method) {
          return { conversation: records.get(id) }
        }
        if (path.startsWith("/conversations/") && options.method === "PUT") {
          records.set(
            id,
            options.body as ReturnType<typeof backendConversation>,
          )
          return { conversation: options.body }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(
      services.conversations.updateConfiguration("chat-a", {
        systemPrompt: "Updated prompt",
        sourceIds: ["doc-b"],
        modelConfiguration: {
          llmModel: "mistral:7b",
          ragPipeline: "reranked",
        },
      }),
    ).resolves.toMatchObject({
      id: "chat-a",
      systemPrompt: "Updated prompt",
      sourceIds: ["doc-b"],
      modelConfiguration: {
        llmModel: "mistral:7b",
        embedder: "all-minilm",
        ragPipeline: "reranked",
      },
    })

    await expect(services.conversations.get("chat-b")).resolves.toMatchObject({
      id: "chat-b",
      systemPrompt: "Second prompt",
      modelConfiguration: { llmModel: "llama3.2:3b" },
    })
  })

  it("renames and updates temporary conversations locally", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient((path) => {
        throw new Error(`Unexpected request: ${path}`)
      }),
    })
    const created = await services.conversations.create({
      title: "Temporary",
      ...createDefaultConversationDraft(),
      temporary: true,
    })

    await expect(
      services.conversations.rename(created.id, "Renamed temporary"),
    ).resolves.toMatchObject({ title: "Renamed temporary", temporary: true })
    await expect(
      services.conversations.updateConfiguration(created.id, {
        systemPrompt: "Local prompt",
        modelConfiguration: { llmModel: "local-model" },
      }),
    ).resolves.toMatchObject({
      title: "Renamed temporary",
      systemPrompt: "Local prompt",
      modelConfiguration: { llmModel: "local-model" },
      temporary: true,
    })
  })

  it("sends non-streaming chat requests with history and settings", async () => {
    const calls: ApiCall[] = []
    const storage = createMemoryStorage("chat-key")
    const services = createHttpServices({
      apiKeyStorage: storage,
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return {
            conversation: backendConversation({
              id: "chat-a",
              title: "Chat",
              settings: {
                llmModel: "qwen3:4b",
                embedderModel: "all-minilm",
                ragPipeline: "basic",
              },
              metadata: {
                frontend: {
                  systemPrompt: "Answer like a concise local assistant.",
                  sourceIds: ["doc-1"],
                },
              },
            }),
          }
        }
        if (path === "/chat" && options.method === "POST") {
          return {
            model: "qwen3:4b",
            answer: "Backend answer",
            ragUsed: true,
            ragWarnings: ["Skipped one stale source."],
            rerankingUsed: true,
            rerankerModel: "bge-reranker",
            rerankWarnings: [],
            compressionUsed: true,
            compressorMode: "token",
            compressionWarnings: ["Trimmed older history."],
            sources: [
              backendChatSource({
                sourceNumber: 1,
                documentName: "notes.txt",
                vectorScore: 0.72,
                rerankScore: 0.91,
              }),
            ],
          }
        }
        if (path === "/conversations/chat-a" && options.method === "PUT") {
          return { conversation: options.body }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(
      services.messages.send({
        conversationId: "chat-a",
        content: "What changed?",
        attachmentIds: ["doc-1"],
      }),
    ).resolves.toMatchObject({
      role: "assistant",
      content: "Backend answer",
      status: "complete",
      metadata: {
        ragUsed: true,
        ragWarnings: ["Skipped one stale source."],
        rerankingUsed: true,
        rerankerModel: "bge-reranker",
        compressionUsed: true,
        compressorMode: "token",
        compressionWarnings: ["Trimmed older history."],
        sources: [
          expect.objectContaining({
            sourceNumber: 1,
            documentName: "notes.txt",
            vectorScore: 0.72,
            rerankScore: 0.91,
          }),
        ],
      },
    })

    const chatCall = calls.find((call) => call.path === "/chat")
    expect(chatCall).toMatchObject({
      path: "/chat",
      options: {
        method: "POST",
        headers: { Authorization: "Bearer chat-key" },
        body: {
          conversationId: "chat-a",
          message: "What changed?",
          systemPrompt: "Answer like a concise local assistant.",
          conversationSettings: {
            llmModel: "qwen3:4b",
            embedderModel: "all-minilm",
            ragPipeline: "basic",
          },
          attachmentDocumentIds: ["doc-1"],
          ragOptions: {
            enabled: true,
            includeSources: true,
            documentIds: ["doc-1"],
          },
        },
      },
    })
    expect(chatCall?.options.body).toMatchObject({
      history: [{ role: "user", content: "Hello" }],
    })
    const persistCall = calls.find(
      (call) =>
        call.path === "/conversations/chat-a" && call.options.method === "PUT",
    )
    expect(persistCall?.options.body).toMatchObject({
      messages: [
        { role: "user", content: "Hello" },
        { role: "user", content: "What changed?" },
        { role: "assistant", content: "Backend answer", status: "complete" },
      ],
    })
  })

  it("sends selected source IDs as RAG document IDs", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return {
            conversation: backendConversation({
              id: "chat-a",
              metadata: {
                frontend: { sourceIds: ["doc-a", "doc-b"] },
              },
            }),
          }
        }
        if (path === "/chat" && options.method === "POST") {
          return { model: "qwen3:4b", answer: "Backend answer" }
        }
        if (path === "/conversations/chat-a" && options.method === "PUT") {
          return { conversation: options.body }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.messages.send({
      conversationId: "chat-a",
      content: "Use selected docs",
      attachmentIds: [],
    })

    expect(
      calls.find((call) => call.path === "/chat")?.options.body,
    ).toMatchObject({
      attachmentDocumentIds: [],
      ragOptions: {
        enabled: true,
        includeSources: true,
        documentIds: ["doc-a", "doc-b"],
      },
    })
  })

  it("deduplicates selected and attached document IDs for RAG requests", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return {
            conversation: backendConversation({
              id: "chat-a",
              metadata: {
                frontend: { sourceIds: ["doc-a", "doc-b"] },
              },
            }),
          }
        }
        if (path === "/chat" && options.method === "POST") {
          return { model: "qwen3:4b", answer: "Backend answer" }
        }
        if (path === "/conversations/chat-a" && options.method === "PUT") {
          return { conversation: options.body }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.messages.send({
      conversationId: "chat-a",
      content: "Use selected and attached docs",
      attachmentIds: ["doc-b", "doc-c", "doc-c"],
    })

    expect(
      calls.find((call) => call.path === "/chat")?.options.body,
    ).toMatchObject({
      attachmentDocumentIds: ["doc-b", "doc-c"],
      ragOptions: {
        documentIds: ["doc-a", "doc-b", "doc-c"],
      },
    })
  })

  it("does not enable RAG options when no sources are selected or attached", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        if (path === "/chat" && options.method === "POST") {
          return { model: "qwen3:4b", answer: "Backend answer" }
        }
        if (path === "/conversations/chat-a" && options.method === "PUT") {
          return { conversation: options.body }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.messages.send({
      conversationId: "chat-a",
      content: "Plain chat",
      attachmentIds: [],
    })

    expect(
      calls.find((call) => call.path === "/chat")?.options.body,
    ).toMatchObject({
      attachmentDocumentIds: [],
    })
    expect(
      (calls.find((call) => call.path === "/chat")?.options.body as {
        ragOptions?: unknown
      }).ragOptions,
    ).toBeUndefined()
  })

  it("keeps completed messages locally when backend transcript persistence fails", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        if (path === "/chat" && options.method === "POST") {
          return { model: "qwen3:4b", answer: "Backend answer" }
        }
        if (path === "/conversations/chat-a" && options.method === "PUT") {
          throw new AppError("Persist failed", { status: 500, code: "server" })
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await expect(
      services.messages.send({
        conversationId: "chat-a",
        content: "Persist this",
        attachmentIds: [],
      }),
    ).resolves.toMatchObject({
      role: "assistant",
      content: "Backend answer",
      status: "complete",
    })
    await expect(services.conversations.get("chat-a")).resolves.toMatchObject({
      messages: [
        { role: "user", content: "Hello" },
        { role: "user", content: "Persist this" },
        { role: "assistant", content: "Backend answer" },
      ],
    })
  })

  it("maps backend SSE tokens and done into stream events", async () => {
    const fetchCalls: FetchCall[] = []
    const apiCalls: ApiCall[] = []
    const storage = createMemoryStorage("stream-key")
    const services = createHttpServices({
      apiKeyStorage: storage,
      apiBaseUrl: "http://api.test",
      fetchImplementation: async (url, init) => {
        fetchCalls.push({ url: String(url), init })
        return sseResponse([
          'event: progress\ndata: {"stage":"generating"}\n\n',
          'event: metadata\ndata: {"model":"qwen3:4b","ragUsed":true,"sources":[{"sourceNumber":1,"documentId":"doc-a","documentName":"notes.txt","chunkId":"chunk-a","chunkIndex":0,"score":0.7,"vectorScore":0.7,"rerankScore":0.9,"finalRank":1,"textPreview":"Relevant note."}]}\n\n',
          'event: token\ndata: {"text":"One "}\n\n',
          'event: token\ndata: {"text":"stream"}\n\n',
          'event: done\ndata: {"answer":"One stream","model":"qwen3:4b","ragUsed":true,"sources":[{"sourceNumber":1,"documentId":"doc-a","documentName":"notes.txt","chunkId":"chunk-a","chunkIndex":0,"score":0.7,"vectorScore":0.7,"rerankScore":0.9,"finalRank":1,"textPreview":"Relevant note."}]}\n\n',
        ])
      },
      apiClient: createFakeApiClient((path, options) => {
        apiCalls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        if (path === "/conversations/chat-a" && options.method === "PUT") {
          return { conversation: options.body }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    const events = []
    for await (const event of services.messages.stream({
      conversationId: "chat-a",
      content: "Hello backend",
      attachmentIds: [],
    })) {
      events.push(event)
    }

    expect(events).toEqual([
      expect.objectContaining({
        type: "accepted",
        userMessage: expect.objectContaining({
          role: "user",
          content: "Hello backend",
        }),
        assistantMessage: expect.objectContaining({
          role: "assistant",
          status: "pending",
        }),
      }),
      {
        type: "delta",
        messageId: expect.any(String),
        delta: "One ",
      },
      {
        type: "delta",
        messageId: expect.any(String),
        delta: "stream",
      },
      expect.objectContaining({
        type: "complete",
        message: expect.objectContaining({
          role: "assistant",
          content: "One stream",
          status: "complete",
          metadata: {
            model: "qwen3:4b",
            ragUsed: true,
            ragWarnings: [],
            rerankingUsed: undefined,
            rerankerModel: null,
            rerankWarnings: [],
            compressionUsed: undefined,
            compressorMode: undefined,
            compressionWarnings: [],
            sources: [
              {
                sourceNumber: 1,
                documentId: "doc-a",
                documentName: "notes.txt",
                chunkId: "chunk-a",
                chunkIndex: 0,
                score: 0.7,
                vectorScore: 0.7,
                rerankScore: 0.9,
                finalRank: 1,
                textPreview: "Relevant note.",
                pageNumber: null,
                collectionId: null,
              },
            ],
          },
        }),
      }),
    ])
    expect(fetchCalls[0].url).toBe("http://api.test/chat/stream")
    expect(fetchCalls[0].init?.method).toBe("POST")
    expect(fetchCalls[0].init?.credentials).toBe("include")
    expect((fetchCalls[0].init?.headers as Headers).get("Authorization")).toBe(
      "Bearer stream-key",
    )
    expect(JSON.parse(String(fetchCalls[0].init?.body))).toMatchObject({
      conversationId: "chat-a",
      message: "Hello backend",
      history: [{ role: "user", content: "Hello" }],
    })

    await expect(services.conversations.get("chat-a")).resolves.toMatchObject({
      messages: [
        { role: "user", content: "Hello" },
        { role: "user", content: "Hello backend" },
        { role: "assistant", content: "One stream" },
      ],
    })
    expect(
      apiCalls.find((call) => call.options.method === "PUT")?.options.body,
    ).toMatchObject({
      messages: [
        { role: "user", content: "Hello" },
        { role: "user", content: "Hello backend" },
        { role: "assistant", content: "One stream", status: "complete" },
      ],
    })
  })

  it("maps backend SSE error events to failed messages", async () => {
    const services = createHttpServices({
      apiBaseUrl: "http://api.test",
      fetchImplementation: async () =>
        sseResponse([
          'event: token\ndata: {"text":"partial"}\n\n',
          'event: error\ndata: {"status":503,"message":"Ollama offline"}\n\n',
        ]),
      apiClient: createFakeApiClient((path, options) => {
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    const events = []
    for await (const event of services.messages.stream({
      conversationId: "chat-a",
      content: "Hello backend",
      attachmentIds: [],
    })) {
      events.push(event)
    }

    expect(events.at(-1)).toMatchObject({
      type: "failed",
      message: { status: "failed", error: "Ollama offline" },
    })
  })

  it("normalizes stream disconnects before done as failed messages", async () => {
    const services = createHttpServices({
      apiBaseUrl: "http://api.test",
      fetchImplementation: async () =>
        sseResponse(['event: token\ndata: {"text":"partial"}\n\n']),
      apiClient: createFakeApiClient((path, options) => {
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    const events = []
    for await (const event of services.messages.stream({
      conversationId: "chat-a",
      content: "Hello backend",
      attachmentIds: [],
    })) {
      events.push(event)
    }

    expect(events.at(-1)).toMatchObject({
      type: "failed",
      message: {
        status: "failed",
        error: "Streaming response ended before completion.",
      },
    })
  })

  it("lists backend documents as proposed sources for the active conversation", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations") {
          return {
            conversations: [
              backendConversation({ id: "chat-a", title: "Alpha" }),
            ],
          }
        }
        if (path === "/documents?conversationId=chat-a") {
          return {
            conversationId: "chat-a",
            documents: [
              backendDocument({
                documentId: "doc-indexed",
                originalFilename: "ready.pdf",
                status: "indexed",
              }),
              backendDocument({
                documentId: "doc-uploaded",
                originalFilename: "queued.txt",
                status: "uploaded",
              }),
              backendDocument({
                documentId: "doc-failed",
                originalFilename: "bad.pdf",
                status: "failed",
                error: "Malformed PDF",
              }),
            ],
          }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.conversations.list()
    await expect(services.sources.list()).resolves.toEqual([
      expect.objectContaining({
        id: "doc-indexed",
        filename: "ready.pdf",
        status: "ready",
      }),
      expect.objectContaining({
        id: "doc-uploaded",
        filename: "queued.txt",
        status: "processing",
      }),
      expect.objectContaining({
        id: "doc-failed",
        filename: "bad.pdf",
        status: "failed",
        error: "Malformed PDF",
      }),
    ])
    expect(calls.at(-1)?.path).toBe("/documents?conversationId=chat-a")
  })

  it("uploads source files to the backend document upload endpoint", async () => {
    const calls: ApiCall[] = []
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        calls.push({ path, options })
        if (path === "/conversations/chat-a" && !options.method) {
          return {
            conversation: backendConversation({
              id: "chat-a",
              settings: { llmModel: "qwen3:4b", chunker: "recursive" },
            }),
          }
        }
        if (path === "/documents/upload" && options.method === "POST") {
          return backendDocument({
            documentId: "doc-uploaded",
            originalFilename: "notes.txt",
            status: "uploaded",
          })
        }
        if (
          path === "/documents/doc-uploaded/process/jobs" &&
          options.method === "POST"
        ) {
          return backendJob({ id: "job-process" })
        }
        if (path === "/jobs/job-process") {
          return backendJob({
            id: "job-process",
            state: "succeeded",
            result: {
              document: backendDocument({
                documentId: "doc-uploaded",
                originalFilename: "notes.txt",
                status: "processed",
              }),
            },
          })
        }
        if (
          path === "/documents/doc-uploaded/index/jobs" &&
          options.method === "POST"
        ) {
          return backendJob({ id: "job-index" })
        }
        if (path === "/jobs/job-index") {
          return backendJob({
            id: "job-index",
            state: "succeeded",
            result: { indexedChunks: 1 },
          })
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.conversations.get("chat-a")
    await expect(
      services.sources.upload([
        new File(["hello"], "notes.txt", { type: "text/plain" }),
      ]),
    ).resolves.toEqual([
      expect.objectContaining({
        id: "doc-uploaded",
        filename: "notes.txt",
        status: "ready",
      }),
    ])

    const uploadCall = calls.find((call) => call.path === "/documents/upload")
    expect(uploadCall?.options.formData).toBeInstanceOf(FormData)
    expect(uploadCall?.options.formData?.get("conversationId")).toBe("chat-a")
    expect(uploadCall?.options.formData?.get("conversationSettings")).toContain(
      '"chunker":"recursive"',
    )
    expect(uploadCall?.options.formData?.get("file")).toBeInstanceOf(File)
    expect(calls.map((call) => call.path)).toEqual([
      "/conversations/chat-a",
      "/documents/upload",
      "/documents/doc-uploaded/process/jobs",
      "/jobs/job-process",
      "/documents/doc-uploaded/index/jobs",
      "/jobs/job-index",
    ])
  })

  it("returns a failed source when document indexing jobs fail", async () => {
    const services = createHttpServices({
      jobPollIntervalMs: 0,
      apiClient: createFakeApiClient((path, options) => {
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        if (path === "/documents/upload" && options.method === "POST") {
          return backendDocument({
            documentId: "doc-failed",
            originalFilename: "notes.txt",
            status: "uploaded",
          })
        }
        if (path === "/documents/doc-failed/process/jobs") {
          return backendJob({ id: "job-process" })
        }
        if (path === "/jobs/job-process") {
          return backendJob({
            id: "job-process",
            state: "succeeded",
            result: {
              document: backendDocument({
                documentId: "doc-failed",
                originalFilename: "notes.txt",
                status: "processed",
              }),
            },
          })
        }
        if (path === "/documents/doc-failed/index/jobs") {
          return backendJob({ id: "job-index" })
        }
        if (path === "/jobs/job-index") {
          return backendJob({
            id: "job-index",
            state: "failed",
            error: "Embedder unavailable",
          })
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.conversations.get("chat-a")
    await expect(
      services.sources.upload([
        new File(["hello"], "notes.txt", { type: "text/plain" }),
      ]),
    ).resolves.toEqual([
      expect.objectContaining({
        id: "doc-failed",
        status: "failed",
        error: "Embedder unavailable",
      }),
    ])
  })

  it("retries source processing and indexing jobs", async () => {
    const calls: string[] = []
    const services = createHttpServices({
      jobPollIntervalMs: 0,
      apiClient: createFakeApiClient((path, options) => {
        calls.push(path)
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        if (path === "/documents/doc-a?conversationId=chat-a") {
          return backendDocument({
            documentId: "doc-a",
            originalFilename: "retry.txt",
            status: "failed",
            error: "Previous failure",
          })
        }
        if (path === "/documents/doc-a/process/jobs") {
          return backendJob({ id: "job-process" })
        }
        if (path === "/jobs/job-process") {
          return backendJob({
            id: "job-process",
            state: "succeeded",
            result: {
              document: backendDocument({
                documentId: "doc-a",
                originalFilename: "retry.txt",
                status: "processed",
              }),
            },
          })
        }
        if (path === "/documents/doc-a/index/jobs") {
          return backendJob({ id: "job-index" })
        }
        if (path === "/jobs/job-index") {
          return backendJob({
            id: "job-index",
            state: "succeeded",
            result: { indexedChunks: 2 },
          })
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.conversations.get("chat-a")
    await expect(services.sources.retry("doc-a")).resolves.toMatchObject({
      id: "doc-a",
      filename: "retry.txt",
      status: "ready",
      error: undefined,
    })
    expect(calls).toEqual([
      "/conversations/chat-a",
      "/documents/doc-a?conversationId=chat-a",
      "/documents/doc-a/process/jobs",
      "/jobs/job-process",
      "/documents/doc-a/index/jobs",
      "/jobs/job-index",
    ])
  })

  it("loads source summaries from backend document chunks", async () => {
    const services = createHttpServices({
      apiClient: createFakeApiClient((path, options) => {
        if (path === "/conversations/chat-a" && !options.method) {
          return { conversation: backendConversation({ id: "chat-a" }) }
        }
        if (path === "/documents/doc-a/chunks?conversationId=chat-a") {
          return {
            chunks: [
              { text: "First extracted chunk." },
              { text: "Second extracted chunk." },
              { text: "Third extracted chunk." },
              { text: "Fourth chunk is omitted." },
            ],
          }
        }
        throw new Error(`Unexpected request: ${path}`)
      }),
    })

    await services.conversations.get("chat-a")
    await expect(services.sources.getSummary("doc-a")).resolves.toEqual([
      "First extracted chunk.",
      "Second extracted chunk.",
      "Third extracted chunk.",
    ])
  })
})

afterEach(() => {
  vi.useRealTimers()
  localStorage.clear()
})

function backendConversation(
  overrides: Partial<{
    id: string
    title: string
    updatedAt: string
    settings: Record<string, string>
    metadata: Record<string, unknown>
  }> = {},
) {
  return {
    id: overrides.id ?? "chat-a",
    title: overrides.title ?? "Alpha",
    messages: [
      {
        role: "user",
        content: "Hello",
        createdAt: "2026-07-20T12:00:00.000Z",
      },
    ],
    settings: overrides.settings ?? { llmModel: "llama3.2:3b" },
    metadata: overrides.metadata ?? {},
    attachmentReferences: [],
    createdAt: overrides.updatedAt ?? "2026-07-20T12:00:00.000Z",
    updatedAt: overrides.updatedAt ?? "2026-07-20T12:00:00.000Z",
  }
}

function backendDocument(
  overrides: Partial<{
    documentId: string
    originalFilename: string
    mimeType: string
    size: number
    createdAt: string
    status: string
    error: string
  }> = {},
) {
  return {
    documentId: overrides.documentId ?? "doc-a",
    originalFilename: overrides.originalFilename ?? "document.txt",
    mimeType: overrides.mimeType ?? "text/plain",
    size: overrides.size ?? 42,
    createdAt: overrides.createdAt ?? "2026-07-20T12:00:00.000Z",
    status: overrides.status ?? "uploaded",
    error: overrides.error,
  }
}

function backendJob(
  overrides: Partial<{
    id: string
    state: string
    progress: number
    result: Record<string, unknown>
    error: string
  }> = {},
) {
  return {
    job: {
      id: overrides.id ?? "job-a",
      type: "document.process",
      state: overrides.state ?? "queued",
      progress: overrides.progress ?? 0,
      result: overrides.result,
      error: overrides.error,
      createdAt: "2026-07-20T12:00:00.000Z",
      updatedAt: "2026-07-20T12:00:00.000Z",
    },
  }
}

function backendChatSource(
  overrides: Partial<{
    sourceNumber: number
    documentId: string
    documentName: string
    chunkId: string
    chunkIndex: number
    score: number
    vectorScore: number
    rerankScore: number
    finalRank: number
    textPreview: string
    pageNumber: number
  }> = {},
) {
  return {
    sourceNumber: overrides.sourceNumber ?? 1,
    documentId: overrides.documentId ?? "doc-a",
    documentName: overrides.documentName ?? "Document",
    chunkId: overrides.chunkId ?? "chunk-a",
    chunkIndex: overrides.chunkIndex ?? 0,
    score: overrides.score ?? 0.5,
    vectorScore: overrides.vectorScore ?? 0.5,
    rerankScore: overrides.rerankScore ?? null,
    finalRank: overrides.finalRank ?? 1,
    textPreview: overrides.textPreview ?? "Relevant text.",
    pageNumber: overrides.pageNumber ?? null,
  }
}

function sseResponse(chunks: string[], status = 200): Response {
  const encoder = new TextEncoder()
  return new Response(
    new ReadableStream({
      start(controller) {
        chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)))
        controller.close()
      },
    }),
    {
      status,
      headers: { "Content-Type": "text/event-stream" },
    },
  )
}
