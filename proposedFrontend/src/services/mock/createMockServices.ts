import type {
  AccountStatus,
  AuthSession,
  ChatMessage,
  ComponentCapabilities,
  Conversation,
  ConversationSummary,
  SourceDocument,
} from "../../domain/models"
import type {
  AppServices,
  AuthService,
  ConversationService,
  DiagnosticsService,
  DiagnosticsStatus,
  MessageService,
  MessageStreamEvent,
  RepositoryService,
  SourceService,
} from "../contracts"
import { AppError } from "../errors"
import {
  createMockProfileService,
  type ProfileMockOperation,
} from "./createMockProfileService"

export type MockOperation = "auth.createAccount" | "auth.getOAuthRedirect" | "auth.requestEmailVerification" | "auth.restoreSession" | "auth.signIn" | "auth.signOut" | "auth.verifyEmailCode" | "conversations.create" | "conversations.delete" | "conversations.get" | "conversations.list" | "conversations.rename" | "conversations.updateConfiguration" | "diagnostics.status" | "diagnostics.supportBundle" | "messages.cancel" | "messages.retry" | "messages.send" | "repositories.ask" | "repositories.indexLocal" | "repositories.indexVector" | "repositories.searchVector" | "sources.delete" | "sources.getSummary" | "sources.list" | "sources.retry" | "sources.upload" | ProfileMockOperation

export interface MockServiceControl {
  failNext(operation: MockOperation, error?: AppError): void
  reset(): void
  setLatency(minimumMs: number, maximumMs?: number): void
}

export interface MockServiceBundle {
  services: AppServices
  control: MockServiceControl
}

const MOCK_SESSION_KEY = "localchat.mock-session"
const MOCK_DATA_KEY = "localchat.mock-data.v1"

interface StoredMockData {
  version: 1
  conversations: Conversation[]
  sources: SourceDocument[]
}

export function createMockServices(): MockServiceBundle {
  const state = createState()
  const failures = new Map<MockOperation, AppError[]>()
  const cancelledMessageIds = new Set<string>()
  let latency = { minimumMs: 90, maximumMs: 180 }

  const simulate = async (operation: MockOperation) => {
    const duration =
      latency.minimumMs +
      Math.round(Math.random() * (latency.maximumMs - latency.minimumMs))
    await new Promise((resolve) => globalThis.setTimeout(resolve, duration))

    const queuedFailures = failures.get(operation)
    const failure = queuedFailures?.shift()
    if (queuedFailures?.length === 0) failures.delete(operation)
    if (failure) throw failure
  }

  const profileMock = createMockProfileService(simulate)

  const auth: AuthService = {
    async signIn(input) {
      await simulate("auth.signIn")
      if (input.username !== "test" || input.password !== "test") {
        throw new AppError(
          'Incorrect username or password. Try "test" for both fields.',
          { code: "unauthorized", status: 401 },
        )
      }
      state.session = createSession("test", "test@email.com")
      writeStoredSession(state.session)
      return clone(state.session)
    },
    async signOut() {
      await simulate("auth.signOut")
      state.session = null
      clearStoredSession()
    },
    async restoreSession() {
      await simulate("auth.restoreSession")
      const restored = state.session ?? readStoredSession()
      if (!restored || Date.parse(restored.expiresAt) <= Date.now()) {
        state.session = null
        clearStoredSession()
        return null
      }
      state.session = restored
      return clone(restored)
    },
    async requestEmailVerification(email) {
      await simulate("auth.requestEmailVerification")
      if (email.toLowerCase() !== "test@email.com") {
        throw new AppError("For this demo, enter test@email.com.", {
          code: "validation",
          status: 422,
        })
      }
      state.verificationEmail = email.toLowerCase()
      state.emailVerified = false
    },
    async verifyEmailCode(input) {
      await simulate("auth.verifyEmailCode")
      if (
        input.email.toLowerCase() !== state.verificationEmail ||
        input.code !== "12345"
      ) {
        throw new AppError(
          "That code is not correct. Use 12345 for this demo.",
          { code: "validation", status: 422 },
        )
      }
      state.emailVerified = true
    },
    async createAccount(input) {
      await simulate("auth.createAccount")
      if (
        input.email.toLowerCase() !== state.verificationEmail ||
        !state.emailVerified
      ) {
        throw new AppError(
          "Verify the email address before creating an account.",
          {
            code: "validation",
            status: 422,
          },
        )
      }
      state.session = createSession("test", input.email.toLowerCase())
      writeStoredSession(state.session)
      return clone(state.session)
    },
    async getOAuthRedirect(provider, returnTo) {
      await simulate("auth.getOAuthRedirect")
      const parameters = new URLSearchParams({ provider, returnTo })
      return {
        provider,
        url: `/mock-oauth/authorize?${parameters.toString()}`,
      }
    },
  }

  let storedApiKey = "local-mock-key"

  const account = {
    getStoredApiKey() {
      return storedApiKey
    },
    setStoredApiKey(apiKey: string) {
      storedApiKey = apiKey
    },
    async getStatus(apiKey = storedApiKey): Promise<AccountStatus> {
      return {
        username: state.session?.user.username ?? "test",
        apiKeyConfigured: storedApiKey.length > 0,
        apiKeyActive: apiKey.length > 0 && apiKey === storedApiKey,
      }
    },
    async updateApiKey(apiKey: string): Promise<AccountStatus> {
      storedApiKey = apiKey
      return this.getStatus(apiKey)
    },
  }

  const capabilities = {
    async list(): Promise<ComponentCapabilities> {
      return clone(createMockCapabilities())
    },
  }

  const conversations: ConversationService = {
    async list(input = {}) {
      await simulate("conversations.list")
      const limit = Math.min(Math.max(input.limit ?? 20, 1), 50)
      const offset = Number.parseInt(input.cursor ?? "0", 10) || 0
      const visible = state.conversations
        .filter((conversation) => !conversation.temporary)
        .map(toSummary)
        .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      const items = visible.slice(offset, offset + limit).map(clone)
      return {
        items,
        nextCursor:
          offset + items.length < visible.length
            ? String(offset + items.length)
            : null,
        total: visible.length,
      }
    },
    async get(id) {
      await simulate("conversations.get")
      return clone(requireConversation(state.conversations, id))
    },
    async create(input) {
      await simulate("conversations.create")
      const createdAt = new Date().toISOString()
      const conversation: Conversation = {
        id: createId("conversation"),
        title: input.title?.trim() || "New conversation",
        createdAt,
        updatedAt: createdAt,
        messages: [],
        systemPrompt: input.systemPrompt,
        modelConfiguration: clone(input.modelConfiguration),
        sourceIds: [...input.sourceIds],
        temporary: input.temporary,
      }
      state.conversations.unshift(conversation)
      persistState(state)
      return clone(conversation)
    },
    async rename(id, title) {
      await simulate("conversations.rename")
      const conversation = requireConversation(state.conversations, id)
      conversation.title = title
      conversation.updatedAt = new Date().toISOString()
      persistState(state)
      return clone(toSummary(conversation))
    },
    async delete(id) {
      await simulate("conversations.delete")
      const index = state.conversations.findIndex((item) => item.id === id)
      if (index < 0) throw notFound("Conversation", id)
      state.conversations.splice(index, 1)
      persistState(state)
    },
    async updateConfiguration(id, input) {
      await simulate("conversations.updateConfiguration")
      const conversation = requireConversation(state.conversations, id)
      if (input.systemPrompt !== undefined) {
        conversation.systemPrompt = input.systemPrompt
      }
      if (input.modelConfiguration) {
        conversation.modelConfiguration = {
          ...conversation.modelConfiguration,
          ...input.modelConfiguration,
        }
      }
      if (input.sourceIds) conversation.sourceIds = [...input.sourceIds]
      if (input.temporary !== undefined) {
        conversation.temporary = input.temporary
      }
      conversation.updatedAt = new Date().toISOString()
      persistState(state)
      return clone(conversation)
    },
  }

  const messages: MessageService = {
    async send(input) {
      let completedMessage: ChatMessage | null = null
      for await (const event of this.stream(input)) {
        if (event.type === "complete" || event.type === "failed") {
          completedMessage = event.message
        }
      }
      if (!completedMessage) {
        throw new AppError("The mock response did not complete.", {
          code: "server",
        })
      }
      return completedMessage
    },
    async *stream(input): AsyncIterable<MessageStreamEvent> {
      await simulate("messages.send")
      const conversation = requireConversation(
        state.conversations,
        input.conversationId,
      )
      const createdAt = new Date().toISOString()
      const userMessage: ChatMessage = {
        id: createId("message-user"),
        conversationId: conversation.id,
        role: "user",
        content: input.content,
        status: "complete",
        createdAt,
        attachments: clone(input.attachments ?? []),
      }
      const assistantMessage: ChatMessage = {
        id: createId("message-assistant"),
        conversationId: conversation.id,
        role: "assistant",
        content: "",
        status: "pending",
        createdAt: new Date().toISOString(),
        attachments: [],
      }
      conversation.messages.push(userMessage, assistantMessage)
      if (conversation.title === "New conversation") {
        conversation.title = makeConversationTitle(input.content)
      }
      conversation.updatedAt = assistantMessage.createdAt
      persistState(state)
      yield {
        type: "accepted",
        userMessage: clone(userMessage),
        assistantMessage: clone(assistantMessage),
      }

      if (input.content.toLowerCase().includes("[fail]")) {
        assistantMessage.status = "failed"
        assistantMessage.error =
          "Mock generation failed. Use Retry to recover this response."
        persistState(state)
        yield { type: "failed", message: clone(assistantMessage) }
        return
      }

      const response =
        "Thanks for your message. This response is streaming from the mock message service."
      assistantMessage.status = "streaming"
      for (const chunk of response.match(/\S+\s*/g) ?? [response]) {
        if (cancelledMessageIds.has(assistantMessage.id)) {
          cancelledMessageIds.delete(assistantMessage.id)
          assistantMessage.status = "stopped"
          assistantMessage.error = "Response stopped by the user."
          conversation.updatedAt = new Date().toISOString()
          persistState(state)
          yield { type: "complete", message: clone(assistantMessage) }
          return
        }
        await new Promise((resolve) => globalThis.setTimeout(resolve, 45))
        assistantMessage.content += chunk
        yield {
          type: "delta",
          messageId: assistantMessage.id,
          delta: chunk,
        }
      }

      assistantMessage.status = "complete"
      conversation.updatedAt = new Date().toISOString()
      persistState(state)
      yield { type: "complete", message: clone(assistantMessage) }
    },
    async cancel(conversationId, messageId) {
      await simulate("messages.cancel")
      const conversation = requireConversation(
        state.conversations,
        conversationId,
      )
      const message = requireMessage(conversation, messageId)
      cancelledMessageIds.add(messageId)
      message.status = "stopped"
      message.error = "Response stopped by the user."
      persistState(state)
    },
    async retry(conversationId, messageId) {
      await simulate("messages.retry")
      const conversation = requireConversation(
        state.conversations,
        conversationId,
      )
      const message = requireMessage(conversation, messageId)
      message.status = "complete"
      message.content =
        "Thanks for retrying. This response was regenerated by the mock message service."
      message.error = undefined
      message.createdAt = new Date().toISOString()
      conversation.updatedAt = message.createdAt
      persistState(state)
      return clone(message)
    },
  }

  const sources: SourceService = {
    async list() {
      await simulate("sources.list")
      return state.sources.map(clone)
    },
    async upload(files) {
      await simulate("sources.upload")
      const uploaded = files.map<SourceDocument>((file) => ({
        id: createId("source"),
        filename: file.name,
        mediaType: file.type || "application/octet-stream",
        size: file.size,
        createdAt: new Date().toISOString(),
        status: file.name.toLowerCase().includes("fail") ? "failed" : "ready",
        error: file.name.toLowerCase().includes("fail")
          ? "Mock processing failed. Retry is available."
          : undefined,
      }))
      state.sources.unshift(...uploaded)
      persistState(state)
      return uploaded.map(clone)
    },
    async delete(id) {
      await simulate("sources.delete")
      const index = state.sources.findIndex((source) => source.id === id)
      if (index < 0) throw notFound("Source", id)
      state.sources.splice(index, 1)
      state.conversations.forEach((conversation) => {
        conversation.sourceIds = conversation.sourceIds.filter(
          (sourceId) => sourceId !== id,
        )
      })
      persistState(state)
    },
    async getSummary(id) {
      await simulate("sources.getSummary")
      const source = state.sources.find((item) => item.id === id)
      if (!source) throw notFound("Source", id)
      return [...(source.summary ?? [])]
    },
    async retry(id) {
      await simulate("sources.retry")
      const source = state.sources.find((item) => item.id === id)
      if (!source) throw notFound("Source", id)
      source.status = "ready"
      source.error = undefined
      persistState(state)
      return clone(source)
    },
  }

  const repositories: RepositoryService = {
    async indexLocal(path) {
      await simulate("repositories.indexLocal")
      const repoName = repoNameFromPath(path)
      return {
        repoName,
        indexedFiles: 12,
        indexedChunks: 36,
        freshness: { fresh: true, warnings: [] },
        warnings: [],
      }
    },
    async indexVector(input) {
      await simulate("repositories.indexVector")
      const repoName = repoNameFromPath(input.path)
      return {
        repoName,
        indexedFiles: 12,
        indexedChunks: 36,
        embeddedChunks: 36,
        conversationId: input.conversationId,
        collectionId: `repo-${repoName}`,
        embedderModel: String(
          input.conversationSettings?.embedderModel ?? "all-minilm",
        ),
        vectorDatabase: String(
          input.conversationSettings?.vectorDatabase ?? "chroma",
        ),
        freshness: { fresh: true, warnings: [] },
        warnings: [],
      }
    },
    async ask(input) {
      await simulate("repositories.ask")
      return {
        answer: `Grounded mock answer for ${input.repoName}: ${input.question}`,
        sources: [`${input.repoName}/src/app.py`],
        freshness: { fresh: true, warnings: [] },
        warnings: [],
      }
    },
    async searchVector(input) {
      await simulate("repositories.searchVector")
      return {
        query: input.query,
        warnings: [],
        results: [
          {
            score: 0.87,
            repoName: input.repoName || "sample-repo",
            filePath: "src/app.py",
            startLine: 12,
            endLine: 28,
            language: "python",
            symbolName: "BananaRouter",
            symbolKind: "class",
            text: "class BananaRouter handles repository routing.",
          },
        ],
      }
    },
  }

  const diagnostics: DiagnosticsService = {
    async getStatus() {
      await simulate("diagnostics.status")
      return createMockDiagnosticsStatus()
    },
    async exportSupportBundle() {
      await simulate("diagnostics.supportBundle")
      return {
        filename: "localchat-support-bundle-mock.json",
        mediaType: "application/json",
        content: JSON.stringify(
          {
            generatedAt: new Date().toISOString(),
            redacted: true,
            redactionPolicy:
              "Secrets, sessions, CSRF values, prompts, chat text, document contents, OCR text, and private paths are omitted.",
            diagnostics: createMockDiagnosticsStatus(),
          },
          null,
          2,
        ),
      }
    },
  }

  const control: MockServiceControl = {
    failNext(operation, error) {
      const queue = failures.get(operation) ?? []
      queue.push(
        error ??
          new AppError(`Controlled mock failure for ${operation}.`, {
            code: "server",
            status: 500,
          }),
      )
      failures.set(operation, queue)
    },
    reset() {
      const fresh = createState()
      state.conversations.splice(0, state.conversations.length)
      state.sources.splice(0, state.sources.length, ...fresh.sources)
      state.session = null
      clearStoredSession()
      clearStoredData()
      profileMock.reset()
      state.verificationEmail = null
      state.emailVerified = false
      failures.clear()
      latency = { minimumMs: 90, maximumMs: 180 }
    },
    setLatency(minimumMs, maximumMs = minimumMs) {
      const normalizedMinimum = Math.max(0, minimumMs)
      latency = {
        minimumMs: normalizedMinimum,
        maximumMs: Math.max(normalizedMinimum, maximumMs),
      }
    },
  }

  return {
    services: {
      auth,
      account,
      capabilities,
      conversations,
      messages,
      sources,
      repositories,
      diagnostics,
      profile: profileMock.service,
    },
    control,
  }
}

function repoNameFromPath(path: string): string {
  const normalized = path.replace(/\\/g, "/").split("/").filter(Boolean)
  return normalized.at(-1) || "local-repository"
}

function createMockDiagnosticsStatus(): DiagnosticsStatus {
  return {
    generatedAt: new Date().toISOString(),
    runtime: {
      status: "ok",
      mode: "mock",
      persistence: "browser-local",
    },
    models: {
      ollamaReachable: true,
      activeModel: "llama3.2:3b",
      capabilityDiscovery: "mock",
    },
    documents: {
      totalSources: 5,
      readySources: 5,
      processingSources: 0,
    },
    retrieval: {
      vectorDatabase: "json",
      ragPipelines: ["basic", "hybrid", "reranked"],
    },
    jobs: {
      queued: 0,
      running: 0,
      failed: 0,
    },
    warnings: [],
  }
}

function createMockCapabilities(): ComponentCapabilities {
  return {
    llmModels: [
      createCapability("llama3.2:3b", "LLM Model", "ollama"),
      createCapability("mistral:7b", "LLM Model", "ollama"),
    ],
    embedderModels: [
      createCapability("all-minilm", "Embedder Model", "ollama"),
      createCapability("nomic-embed-text:latest", "Embedder Model", "ollama"),
    ],
    rerankerModels: [
      createCapability("none", "Reranker Model", "builtin"),
      createCapability("bge-reranker-v2:m3", "Reranker Model", "ollama"),
    ],
    visionModels: [
      createCapability("llava:7b", "Vision Model", "ollama"),
      createCapability("minicpm-v:8b", "Vision Model", "ollama"),
    ],
    ocrEngines: [
      createCapability("none", "OCR Engine", "builtin"),
      createCapability("tesseract", "OCR Engine", "local", false),
      createCapability("ocrmypdf", "OCR Engine", "local", false),
    ],
    pdfParsers: [
      createCapability("pymupdf", "PDF Parser", "local"),
      createCapability("pdfplumber", "PDF Parser", "local"),
      createCapability("docling", "PDF Parser", "local", false),
    ],
    chunkers: [
      createCapability("fixed", "Chunker", "static"),
      createCapability("recursive", "Chunker", "static"),
      createCapability("semantic", "Chunker", "static", false),
    ],
    vectorDatabases: [
      createCapability("chroma", "Vector Database", "static", false),
      createCapability("faiss", "Vector Database", "static", false),
      createCapability("qdrant", "Vector Database", "static", false),
      createCapability("lancedb", "Vector Database", "static", false),
    ],
    ragPipelines: [
      createCapability("basic", "RAG Pipeline", "static"),
      createCapability("hybrid", "RAG Pipeline", "static"),
      createCapability("reranked", "RAG Pipeline", "static"),
    ],
    contextCompressors: [
      createCapability("none", "Context Compressor", "static"),
      createCapability("token", "Context Compressor", "static"),
      createCapability("summarizer", "Context Compressor", "static"),
    ],
    unknownOllamaModels: [],
  }
}

function createCapability(
  id: string,
  type: string,
  source: string,
  available = true,
) {
  return {
    id,
    label: id,
    type,
    available,
    source,
    name: source === "ollama" ? id : undefined,
  }
}

function createState() {
  const stored = readStoredData()
  return {
    session: null as AuthSession | null,
    verificationEmail: null as string | null,
    emailVerified: false,
    conversations: stored?.conversations ?? [] as Conversation[],
    sources: stored?.sources ?? createSourceFixtures(),
  }
}

function createSourceFixtures(): SourceDocument[] {
  return [
    createSource(
      "product-roadmap",
      "Product-Roadmap.pdf",
      "application/pdf",
      2_400_000,
      "2026-07-18T14:00:00.000Z",
      [
        "Outlines the next two product releases and their highest-priority customer outcomes.",
        "Highlights dependencies across design, platform, and go-to-market teams.",
        "Calls out authentication improvements and reporting as the next major milestones.",
      ],
    ),
    createSource(
      "customer-research",
      "Customer-Research.docx",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      840_000,
      "2026-07-17T14:00:00.000Z",
      [
        "Summarizes interviews with twelve customers across three primary user groups.",
        "Customers value faster setup, clearer permissions, and simpler reporting workflows.",
        "Includes representative quotes and recommended opportunities for the product team.",
      ],
    ),
    createSource(
      "q2-financials",
      "Q2-Financials.xlsx",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      1_100_000,
      "2026-07-15T14:00:00.000Z",
      [
        "Provides a mock overview of quarterly revenue, operating costs, and budget variance.",
        "Revenue finished slightly above plan while infrastructure costs increased.",
        "The workbook includes department-level tabs and a consolidated summary sheet.",
      ],
    ),
    createSource(
      "meeting-notes",
      "Meeting-Notes.txt",
      "text/plain",
      18_000,
      "2026-07-12T14:00:00.000Z",
      [
        "Captures decisions and follow-up actions from the weekly product review.",
        "The team agreed to validate the onboarding flow before expanding the beta.",
        "Owners and target dates are listed for each open action item.",
      ],
    ),
    createSource(
      "architecture-diagram",
      "Architecture-Diagram.png",
      "image/png",
      3_800_000,
      "2026-07-10T14:00:00.000Z",
      [
        "Shows the main application, model, storage, and document-processing boundaries.",
        "Arrows illustrate the intended request flow between the browser and local services.",
        "The diagram is conceptual and does not represent deployed infrastructure.",
      ],
    ),
  ]
}

function createSource(
  id: string,
  filename: string,
  mediaType: string,
  size: number,
  createdAt: string,
  summary: string[],
): SourceDocument {
  return { id, filename, mediaType, size, createdAt, status: "ready", summary }
}

function createSession(username: string, email: string): AuthSession {
  return {
    accessToken: `mock-token-${createId("session")}`,
    expiresAt: new Date(Date.now() + 60 * 60 * 1_000).toISOString(),
    user: { id: "user-test", username, email, displayName: "Test User" },
  }
}

function requireConversation(
  conversations: Conversation[],
  id: string,
): Conversation {
  const conversation = conversations.find((item) => item.id === id)
  if (!conversation) throw notFound("Conversation", id)
  return conversation
}

function requireMessage(conversation: Conversation, id: string): ChatMessage {
  const message = conversation.messages.find((item) => item.id === id)
  if (!message) throw notFound("Message", id)
  return message
}

function toSummary(conversation: Conversation): ConversationSummary {
  return {
    id: conversation.id,
    title: conversation.title,
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
    temporary: conversation.temporary,
  }
}

function notFound(resource: string, id: string): AppError {
  return new AppError(`${resource} ${id} was not found.`, {
    code: "not_found",
    status: 404,
  })
}

function makeConversationTitle(message: string): string {
  return message.length > 38 ? `${message.slice(0, 38)}…` : message
}

function createId(prefix: string): string {
  return `${prefix}-${globalThis.crypto?.randomUUID?.() ?? Date.now()}`
}

function clone<Value>(value: Value): Value {
  return structuredClone(value)
}

function readStoredSession(): AuthSession | null {
  try {
    const serialized = globalThis.sessionStorage?.getItem(MOCK_SESSION_KEY)
    return serialized ? JSON.parse(serialized) as AuthSession : null
  } catch {
    return null
  }
}

function writeStoredSession(session: AuthSession) {
  try {
    globalThis.sessionStorage?.setItem(
      MOCK_SESSION_KEY,
      JSON.stringify(session),
    )
  } catch {
    // Session storage may be unavailable in tests or privacy-restricted contexts.
  }
}

function clearStoredSession() {
  try {
    globalThis.sessionStorage?.removeItem(MOCK_SESSION_KEY)
  } catch {
    // Session storage may be unavailable in tests or privacy-restricted contexts.
  }
}

function readStoredData(): StoredMockData | null {
  try {
    const serialized = globalThis.localStorage?.getItem(MOCK_DATA_KEY)
    if (!serialized) return null
    const value: unknown = JSON.parse(serialized)
    if (!isStoredMockData(value)) {
      globalThis.localStorage?.removeItem(MOCK_DATA_KEY)
      return null
    }
    const restored = clone(value)
    restored.conversations.forEach((conversation) => {
      conversation.messages.forEach((message) => {
        if (message.status === "pending" || message.status === "streaming") {
          message.status = "stopped"
          message.error =
            "Response interrupted by page reload. Retry to continue."
        }
      })
    })
    return restored
  } catch {
    return null
  }
}

function persistState(state: ReturnType<typeof createState>) {
  try {
    const data: StoredMockData = {
      version: 1,
      // Temporary chats deliberately remain memory-only.
      conversations: state.conversations.filter(
        (conversation) => !conversation.temporary,
      ),
      sources: state.sources,
    }
    globalThis.localStorage?.setItem(MOCK_DATA_KEY, JSON.stringify(data))
  } catch {
    // The demo remains usable if storage is unavailable or its quota is full.
  }
}

function clearStoredData() {
  try {
    globalThis.localStorage?.removeItem(MOCK_DATA_KEY)
  } catch {
    // Storage may be unavailable in tests or privacy-restricted contexts.
  }
}

function isStoredMockData(value: unknown): value is StoredMockData {
  if (!value || typeof value !== "object") return false
  const candidate = value as Partial<StoredMockData>
  return (
    candidate.version === 1 &&
    Array.isArray(candidate.conversations) &&
    candidate.conversations.every(isStoredConversation) &&
    Array.isArray(candidate.sources) &&
    candidate.sources.every(isStoredSource)
  )
}

function isStoredConversation(value: unknown): value is Conversation {
  if (!value || typeof value !== "object") return false
  const candidate = value as Partial<Conversation>
  return (
    typeof candidate.id === "string" &&
    typeof candidate.title === "string" &&
    typeof candidate.createdAt === "string" &&
    typeof candidate.updatedAt === "string" &&
    Array.isArray(candidate.messages) &&
    typeof candidate.systemPrompt === "string" &&
    Boolean(candidate.modelConfiguration) &&
    Array.isArray(candidate.sourceIds) &&
    typeof candidate.temporary === "boolean"
  )
}

function isStoredSource(value: unknown): value is SourceDocument {
  if (!value || typeof value !== "object") return false
  const candidate = value as Partial<SourceDocument>
  return (
    typeof candidate.id === "string" &&
    typeof candidate.filename === "string" &&
    typeof candidate.mediaType === "string" &&
    typeof candidate.size === "number" &&
    typeof candidate.createdAt === "string" &&
    typeof candidate.status === "string"
  )
}
