import { API_BASE_URL, type ApiClient } from "../../api"
import type {
  AuthSession,
  ChatMessage,
  ChatMessageMetadata,
  ChatSourceCitation,
  Conversation,
  ResponsePreference,
  SourceDocument,
  SourceDocumentStatus,
  UserProfile,
} from "../../domain/models"
import type {
  SendMessageRequestDto,
  SignInRequest,
  UpdateProfileRequestDto,
} from "../../domain/dtos"
import {
  createBrowserApiKeyStorage,
  type ApiKeyStorage,
} from "../apiKeyStorage"
import { normalizeComponentCapabilities } from "../capabilities"
import type {
  AppServices,
  DiagnosticsStatus,
  RepositoryAskResult,
  RepositoryIndexResult,
  RepositoryVectorIndexResult,
  RepositoryVectorSearchResult,
} from "../contracts"
import { AppError } from "../errors"
import {
  cloneConversation,
  createLocalConversation,
  mapBackendConversationToConversation,
  mapConfigurationToBackendSettings,
  mapConversationToBackendRecord,
  toConversationSummary,
  type BackendConversationRecord,
  type BackendConversationListResponse,
  type BackendConversationResponse,
} from "./conversationMapper"

export interface HttpServicesOptions {
  apiClient: ApiClient
  apiKeyStorage?: ApiKeyStorage
  apiBaseUrl?: string
  fetchImplementation?: typeof fetch
  jobPollIntervalMs?: number
  jobPollMaxAttempts?: number
}

export function createHttpServices({
  apiClient,
  apiKeyStorage = createBrowserApiKeyStorage(),
  apiBaseUrl = API_BASE_URL,
  fetchImplementation = fetch,
  jobPollIntervalMs = 1000,
  jobPollMaxAttempts = 120,
}: HttpServicesOptions): AppServices {
  const temporaryConversations = new Map<string, Conversation>()
  const conversationCache = new Map<string, Conversation>()
  const localConversationOverrides = new Set<string>()
  const backendConversationRecords =
    new Map<string, BackendConversationRecord>()
  let activeDocumentConversationId = ""
  const profileStorageKey = "localchat.http-profile.v1"

  const createSession = (response: BackendSessionResponse): AuthSession => {
    const username = response.username
    return {
      accessToken: "",
      expiresAt: new Date(Date.now() + 8 * 60 * 60 * 1000).toISOString(),
      user: {
        id: `local-${username}`,
        username,
        email: `${username}@local.invalid`,
        displayName: username,
      },
    }
  }

  const loadLocalProfilePreferences = (): Partial<UpdateProfileRequestDto> => {
    try {
      const serialized = globalThis.localStorage?.getItem(profileStorageKey)
      if (!serialized) return {}
      const parsed = JSON.parse(serialized) as unknown
      return isProfilePreferences(parsed) ? parsed : {}
    } catch {
      return {}
    }
  }

  const saveLocalProfilePreferences = (input: UpdateProfileRequestDto) => {
    try {
      globalThis.localStorage?.setItem(profileStorageKey, JSON.stringify(input))
    } catch {
      // Local presentation preferences remain optional.
    }
  }

  const buildHttpProfile = async (): Promise<UserProfile> => {
    const [session, account] = await Promise.all([
      apiClient.request<BackendSessionResponse>("/auth/me"),
      apiClient.request<BackendAccountStatusResponse>("/account/status", {
        headers: authorizationHeaders(),
      }),
    ])
    const preferences = loadLocalProfilePreferences()
    const displayName =
      preferences.displayName?.trim() || session.username || account.username
    const handle =
      preferences.handle?.trim() ||
      (session.username || account.username).replace(/[^A-Za-z0-9_.-]/g, ".")
    return {
      id: `local-${account.username || session.username}`,
      displayName,
      handle,
      preferredName: preferences.preferredName?.trim() || displayName,
      avatarUrl: null,
      role: preferences.role?.trim() || "Local user",
      about: preferences.about ?? "",
      preferredLanguage: preferences.preferredLanguage || "en-US",
      responsePreference: preferences.responsePreference || "balanced",
      accountType: "member",
      deviceName: "Local backend",
      joinedAt: new Date(0).toISOString(),
      storageLocation: account.api_key_configured
        ? "Backend account with browser-local profile preferences"
        : "Browser-local profile preferences",
    }
  }

  const notConnected = (operation: string) => {
    return new AppError(
      `${operation} is not connected to the backend yet. Continue using mock mode or complete the next migration phase.`,
      { code: "server", status: 501 },
    )
  }

  const reject = async <Result>(operation: string): Promise<Result> => {
    throw notConnected(operation)
  }

  const fetchBackendConversationRecord = async (id: string) => {
    const response = await apiClient.request<BackendConversationResponse>(
      `/conversations/${encodeURIComponent(id)}`,
    )
    backendConversationRecords.set(id, response.conversation)
    conversationCache.set(
      id,
      mapBackendConversationToConversation(response.conversation),
    )
    return response.conversation
  }

  const rememberDocumentConversation = (conversationId: string) => {
    activeDocumentConversationId = conversationId
  }

  const persistConversation = async (
    conversation: Conversation,
    existingRecord: BackendConversationRecord | null,
  ) => {
    const response = await apiClient.request<BackendConversationResponse>(
      `/conversations/${encodeURIComponent(conversation.id)}`,
      {
        method: "PUT",
        body: mapConversationToBackendRecord(conversation, existingRecord),
      },
    )
    backendConversationRecords.set(conversation.id, response.conversation)
    const updated = mapBackendConversationToConversation(response.conversation)
    conversationCache.set(conversation.id, updated)
    return updated
  }

  const getConversationForMessage = async (id: string) => {
    rememberDocumentConversation(id)
    const temporary = temporaryConversations.get(id)
    if (temporary) return cloneConversation(temporary)
    const cached = conversationCache.get(id)
    if (cached) return cloneConversation(cached)
    return mapBackendConversationToConversation(
      await fetchBackendConversationRecord(id),
    )
  }

  const storeConversationForMessage = (conversation: Conversation) => {
    rememberDocumentConversation(conversation.id)
    if (conversation.temporary) {
      temporaryConversations.set(conversation.id, conversation)
    } else {
      conversationCache.set(conversation.id, conversation)
      localConversationOverrides.add(conversation.id)
    }
  }

  const authorizationHeaders = () => {
    const apiKey = apiKeyStorage.get().trim()
    return apiKey ? { Authorization: `Bearer ${apiKey}` } : undefined
  }

  const streamHeaders = () => {
    const headers = new Headers({
      Accept: "text/event-stream",
      "Content-Type": "application/json",
    })
    const authHeaders = authorizationHeaders()
    if (authHeaders?.Authorization) {
      headers.set("Authorization", authHeaders.Authorization)
    }
    const csrfToken = readCookie("local_ai_csrf")
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken)
    return headers
  }

  const createPendingExchange = async (input: SendMessageRequestDto) => {
    const conversation = await getConversationForMessage(input.conversationId)
    const createdAt = new Date().toISOString()
    const userMessage: ChatMessage = {
      id: createId("message-user"),
      conversationId: conversation.id,
      role: "user",
      content: input.content,
      status: "complete",
      createdAt,
      attachments: input.attachments ?? [],
    }
    const assistantMessage: ChatMessage = {
      id: createId("message-assistant"),
      conversationId: conversation.id,
      role: "assistant",
      content: "",
      status: "pending",
      createdAt,
      attachments: [],
    }
    const acceptedConversation = {
      ...conversation,
      messages: [...conversation.messages, userMessage, assistantMessage],
      updatedAt: createdAt,
    }
    storeConversationForMessage(acceptedConversation)
    return { conversation, acceptedConversation, userMessage, assistantMessage }
  }

  const completeAssistantMessage = (
    acceptedConversation: Conversation,
    assistantMessage: ChatMessage,
    content: string,
    metadata?: ChatMessageMetadata,
  ) => {
    const completedMessage: ChatMessage = {
      ...assistantMessage,
      content,
      status: "complete",
      createdAt: new Date().toISOString(),
      metadata,
    }
    const completedConversation = {
      ...acceptedConversation,
      messages: acceptedConversation.messages.map((message) =>
        message.id === assistantMessage.id ? completedMessage : message,
      ),
      updatedAt: completedMessage.createdAt,
    }
    storeConversationForMessage(completedConversation)
    return { message: completedMessage, conversation: completedConversation }
  }

  const failAssistantMessage = (
    acceptedConversation: Conversation,
    assistantMessage: ChatMessage,
    error: unknown,
  ) => {
    const failedMessage: ChatMessage = {
      ...assistantMessage,
      status: "failed",
      error:
        error instanceof Error ? error.message : "Streaming generation failed.",
    }
    const failedConversation = {
      ...acceptedConversation,
      messages: acceptedConversation.messages.map((message) =>
        message.id === assistantMessage.id ? failedMessage : message,
      ),
      updatedAt: new Date().toISOString(),
    }
    storeConversationForMessage(failedConversation)
    return { message: failedMessage, conversation: failedConversation }
  }

  const persistMessageConversation = async (conversation: Conversation) => {
    if (conversation.temporary) return
    try {
      await persistConversation(
        conversation,
        backendConversationRecords.get(conversation.id) ?? null,
      )
    } catch {
      conversationCache.set(conversation.id, conversation)
      localConversationOverrides.add(conversation.id)
    }
  }

  const buildChatRequestBody = (
    conversation: Conversation,
    input: SendMessageRequestDto,
  ) => {
    const attachmentDocumentIds = uniqueStrings(input.attachmentIds)
    const ragDocumentIds = uniqueStrings([
      ...conversation.sourceIds,
      ...attachmentDocumentIds,
    ])
    return {
      conversationId: conversation.id,
      message: input.content,
      history: conversation.messages
        .filter(
          (message) => message.role === "user" || message.role === "assistant",
        )
        .map((message) => ({
          role: message.role,
          content: message.content,
        })),
      conversationSettings: mapConfigurationToBackendSettings(
        conversation.modelConfiguration,
      ),
      attachmentDocumentIds,
      ragOptions:
        ragDocumentIds.length > 0
          ? {
              enabled: true,
              includeSources: true,
              documentIds: ragDocumentIds,
            }
          : undefined,
    }
  }

  const requireDocumentConversationId = () => {
    if (activeDocumentConversationId) return activeDocumentConversationId
    throw new AppError(
      "Open or create a conversation before using document sources.",
      { code: "validation", status: 400 },
    )
  }

  const activeConversationSettings = () => {
    const conversation = conversationCache.get(activeDocumentConversationId)
    return conversation
      ? mapConfigurationToBackendSettings(conversation.modelConfiguration)
      : undefined
  }

  const uploadSourceFile = async (file: File) => {
    const conversationId = requireDocumentConversationId()
    const formData = new FormData()
    formData.set("conversationId", conversationId)
    formData.set("file", file)
    const settings = activeConversationSettings()
    if (settings) {
      formData.set("conversationSettings", JSON.stringify(settings))
    }
    const response = await apiClient.request<BackendDocumentRecord>(
      "/documents/upload",
      {
        method: "POST",
        formData,
      },
    )
    return processAndIndexSource(mapBackendDocumentToSource(response))
  }

  const processAndIndexSource = async (source: SourceDocument) => {
    if (source.status === "ready") return source
    const conversationId = requireDocumentConversationId()
    const settings = activeConversationSettings()
    const body = {
      conversationId,
      conversationSettings: settings,
    }
    try {
      const processJob = await startDocumentJob(
        `/documents/${encodeURIComponent(source.id)}/process/jobs`,
        body,
      )
      const processedJob = await pollJob(processJob.id)
      if (processedJob.state !== "succeeded") {
        return failedSourceFromJob(source, processedJob)
      }
      const processedDocument = processedJob.result?.document
      const processedSource = isBackendDocumentRecord(processedDocument)
        ? mapBackendDocumentToSource(processedDocument)
        : { ...source, status: "processing" as const }
      if (processedSource.status === "failed") return processedSource

      const indexJob = await startDocumentJob(
        `/documents/${encodeURIComponent(source.id)}/index/jobs`,
        body,
      )
      const indexedJob = await pollJob(indexJob.id)
      if (indexedJob.state !== "succeeded") {
        return failedSourceFromJob(processedSource, indexedJob)
      }
      return {
        ...processedSource,
        status: "ready" as const,
        error: undefined,
      }
    } catch (error) {
      return {
        ...source,
        status: "failed" as const,
        error:
          error instanceof Error
            ? error.message
            : "Document processing failed.",
      }
    }
  }

  const startDocumentJob = async (path: string, body: unknown) => {
    const response = await apiClient.request<BackendJobResponse>(path, {
      method: "POST",
      body,
    })
    return response.job
  }

  const pollJob = async (jobId: string) => {
    for (let attempt = 0; attempt < jobPollMaxAttempts; attempt += 1) {
      const response = await apiClient.request<BackendJobResponse>(
        `/jobs/${encodeURIComponent(jobId)}`,
      )
      if (isTerminalJobState(response.job.state)) return response.job
      if (jobPollIntervalMs > 0) {
        await delay(jobPollIntervalMs)
      }
    }
    throw new AppError("Timed out waiting for document processing job.", {
      code: "timeout",
      status: 408,
    })
  }

  const sendNonStreamingMessage = async (input: SendMessageRequestDto) => {
    const { conversation, acceptedConversation, assistantMessage } =
      await createPendingExchange(input)
    try {
      const response = await apiClient.request<BackendChatResponse>("/chat", {
        method: "POST",
        headers: authorizationHeaders(),
        body: buildChatRequestBody(conversation, input),
      })
      const completed = completeAssistantMessage(
        acceptedConversation,
        assistantMessage,
        response.answer,
        mapChatResponseMetadata(response),
      )
      await persistMessageConversation(completed.conversation)
      return completed.message
    } catch (error) {
      const failed = failAssistantMessage(
        acceptedConversation,
        assistantMessage,
        error,
      )
      await persistMessageConversation(failed.conversation)
      throw error
    }
  }

  async function* streamChatMessage(input: SendMessageRequestDto) {
    const {
      conversation,
      acceptedConversation,
      userMessage,
      assistantMessage,
    } = await createPendingExchange(input)
    yield { type: "accepted" as const, userMessage, assistantMessage }

    let streamedContent = ""
    let streamedMetadata: ChatMessageMetadata | undefined
    try {
      for await (const event of streamBackendChat(
        buildChatRequestBody(conversation, input),
      )) {
        if (event.event === "token") {
          const delta = sseText(event.data, "text")
          if (!delta) continue
          streamedContent += delta
          yield {
            type: "delta" as const,
            messageId: assistantMessage.id,
            delta,
          }
        } else if (event.event === "error") {
          throw new AppError(
            sseText(event.data, "message") || "Streaming generation failed.",
            { status: sseNumber(event.data, "status"), code: "server" },
          )
        } else if (event.event === "metadata") {
          streamedMetadata = mapChatResponseMetadata(event.data)
        } else if (event.event === "done") {
          const answer = sseText(event.data, "answer") || streamedContent
          const completed = completeAssistantMessage(
            acceptedConversation,
            assistantMessage,
            answer,
            mapChatResponseMetadata(event.data) ?? streamedMetadata,
          )
          await persistMessageConversation(completed.conversation)
          yield { type: "complete" as const, message: completed.message }
          return
        }
      }
      throw new AppError("Streaming response ended before completion.", {
        code: "server",
      })
    } catch (error) {
      const failed = failAssistantMessage(
        acceptedConversation,
        assistantMessage,
        error,
      )
      await persistMessageConversation(failed.conversation)
      yield { type: "failed" as const, message: failed.message }
    }
  }

  async function* streamBackendChat(body: unknown) {
    const response = await fetchImplementation(
      resolveUrl(apiBaseUrl, "/chat/stream"),
      {
        method: "POST",
        credentials: "include",
        headers: streamHeaders(),
        body: JSON.stringify(body),
      },
    )
    if (!response.ok) throw await responseError(response)
    if (!response.body?.getReader) {
      throw new AppError("Streaming is not supported by this browser.", {
        code: "server",
      })
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const parsed = parseSseFrames(buffer)
      buffer = parsed.remainder
      for (const frame of parsed.frames) yield parseSseFrame(frame)
    }
    buffer += decoder.decode()
    if (buffer.trim()) yield parseSseFrame(buffer)
  }

  return {
    auth: {
      async signIn(input: SignInRequest) {
        const response = await apiClient.request<BackendSessionResponse>(
          "/auth/login",
          {
            method: "POST",
            body: input,
          },
        )
        return createSession(response)
      },
      async signOut() {
        await apiClient.request<void>("/auth/logout", { method: "POST" })
      },
      async restoreSession() {
        try {
          const response =
            await apiClient.request<BackendSessionResponse>("/auth/me")
          return createSession(response)
        } catch (error) {
          if (
            error instanceof AppError &&
            (error.code === "unauthorized" || error.status === 401)
          ) {
            return null
          }
          throw error
        }
      },
      requestEmailVerification: () => reject("auth.requestEmailVerification"),
      verifyEmailCode: () => reject("auth.verifyEmailCode"),
      createAccount: () => reject("auth.createAccount"),
      getOAuthRedirect: () => reject("auth.getOAuthRedirect"),
    },
    account: {
      getStoredApiKey() {
        return apiKeyStorage.get()
      },
      setStoredApiKey(apiKey: string) {
        apiKeyStorage.set(apiKey)
      },
      async getStatus(apiKey = apiKeyStorage.get()) {
        const headers =
          apiKey.trim().length > 0
            ? { Authorization: `Bearer ${apiKey}` }
            : undefined
        const response = await apiClient.request<BackendAccountStatusResponse>(
          "/account/status",
          { headers },
        )
        return mapAccountStatus(response)
      },
      async updateApiKey(apiKey: string) {
        const response = await apiClient.request<BackendAccountStatusResponse>(
          "/account/api-key",
          {
            method: "PUT",
            body: { apiKey },
          },
        )
        apiKeyStorage.set(apiKey)
        return mapAccountStatus(response)
      },
    },
    capabilities: {
      async list() {
        const response = await apiClient.request<BackendCapabilitiesResponse>(
          "/components/capabilities",
        )
        return normalizeComponentCapabilities(response)
      },
    },
    conversations: {
      async list(input = {}) {
        const response =
          await apiClient.request<BackendConversationListResponse>(
            "/conversations",
          )
        if (!activeDocumentConversationId && response.conversations[0]?.id) {
          rememberDocumentConversation(response.conversations[0].id)
        }
        response.conversations.forEach((record) => {
          backendConversationRecords.set(record.id, record)
          conversationCache.set(
            record.id,
            mapBackendConversationToConversation(record),
          )
        })
        const summaries = response.conversations
          .map(mapBackendConversationToConversation)
          .filter((conversation) => !conversation.temporary)
          .map(toConversationSummary)
          .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
        const offset = Number.parseInt(input.cursor ?? "0", 10) || 0
        const limit = Math.min(Math.max(input.limit ?? 20, 1), 50)
        const items = summaries.slice(offset, offset + limit)
        return {
          items,
          nextCursor:
            offset + items.length < summaries.length
              ? String(offset + items.length)
              : null,
          total: summaries.length,
        }
      },
      async get(id) {
        rememberDocumentConversation(id)
        const temporary = temporaryConversations.get(id)
        if (temporary) return cloneConversation(temporary)
        const cached = conversationCache.get(id)
        if (cached && localConversationOverrides.has(id)) {
          return cloneConversation(cached)
        }
        return mapBackendConversationToConversation(
          await fetchBackendConversationRecord(id),
        )
      },
      async create(input) {
        const conversation = createLocalConversation(input)
        rememberDocumentConversation(conversation.id)
        if (conversation.temporary) {
          temporaryConversations.set(conversation.id, conversation)
          return cloneConversation(conversation)
        }
        const response = await apiClient.request<BackendConversationResponse>(
          "/conversations",
          {
            method: "POST",
            body: mapConversationToBackendRecord(conversation),
          },
        )
        backendConversationRecords.set(conversation.id, response.conversation)
        const created = mapBackendConversationToConversation(
          response.conversation,
        )
        conversationCache.set(conversation.id, created)
        return created
      },
      async rename(id, title) {
        rememberDocumentConversation(id)
        const temporary = temporaryConversations.get(id)
        if (temporary) {
          const updated = {
            ...temporary,
            title: title.trim() || temporary.title,
            updatedAt: new Date().toISOString(),
          }
          temporaryConversations.set(id, updated)
          return toConversationSummary(updated)
        }
        const existingRecord =
          backendConversationRecords.get(id) ??
          (await fetchBackendConversationRecord(id))
        const conversation =
          mapBackendConversationToConversation(existingRecord)
        const updated = await persistConversation(
          {
            ...conversation,
            title: title.trim() || conversation.title,
            updatedAt: new Date().toISOString(),
          },
          existingRecord,
        )
        return toConversationSummary(updated)
      },
      async delete(id) {
        if (temporaryConversations.delete(id)) return
        await apiClient.request<BackendConversationDeleteResponse>(
          `/conversations/${encodeURIComponent(id)}`,
          { method: "DELETE" },
        )
        backendConversationRecords.delete(id)
        conversationCache.delete(id)
        localConversationOverrides.delete(id)
        if (activeDocumentConversationId === id)
          activeDocumentConversationId = ""
      },
      async updateConfiguration(id, input) {
        rememberDocumentConversation(id)
        const temporary = temporaryConversations.get(id)
        if (temporary) {
          const updated = {
            ...temporary,
            systemPrompt: input.systemPrompt ?? temporary.systemPrompt,
            modelConfiguration: {
              ...temporary.modelConfiguration,
              ...(input.modelConfiguration ?? {}),
            },
            sourceIds: input.sourceIds
              ? [...input.sourceIds]
              : temporary.sourceIds,
            temporary: input.temporary ?? temporary.temporary,
            updatedAt: new Date().toISOString(),
          }
          if (updated.temporary) temporaryConversations.set(id, updated)
          else temporaryConversations.delete(id)
          return cloneConversation(updated)
        }
        const existingRecord =
          backendConversationRecords.get(id) ??
          (await fetchBackendConversationRecord(id))
        const conversation =
          mapBackendConversationToConversation(existingRecord)
        return persistConversation(
          {
            ...conversation,
            systemPrompt: input.systemPrompt ?? conversation.systemPrompt,
            modelConfiguration: {
              ...conversation.modelConfiguration,
              ...(input.modelConfiguration ?? {}),
            },
            sourceIds: input.sourceIds
              ? [...input.sourceIds]
              : conversation.sourceIds,
            temporary: input.temporary ?? conversation.temporary,
            updatedAt: new Date().toISOString(),
          },
          existingRecord,
        )
      },
    },
    messages: {
      send: (input) => sendNonStreamingMessage(input),
      stream: (input) => streamChatMessage(input),
      cancel: () => reject("messages.cancel"),
      retry: () => reject("messages.retry"),
    },
    sources: {
      async list() {
        const conversationId = requireDocumentConversationId()
        const response = await apiClient.request<BackendDocumentListResponse>(
          `/documents?conversationId=${encodeURIComponent(conversationId)}`,
        )
        return response.documents.map(mapBackendDocumentToSource)
      },
      async upload(files) {
        const uploaded: SourceDocument[] = []
        for (const file of files) {
          uploaded.push(await uploadSourceFile(file))
        }
        return uploaded
      },
      delete: () => reject("sources.delete"),
      async getSummary(id) {
        const conversationId = requireDocumentConversationId()
        const response = await apiClient.request<BackendDocumentChunksResponse>(
          `/documents/${encodeURIComponent(id)}/chunks?conversationId=${encodeURIComponent(conversationId)}`,
        )
        const chunks = response.chunks
          .map((chunk) => stringFromUnknown(chunk.text).trim())
          .filter(Boolean)
          .slice(0, 3)
        return chunks.length > 0
          ? chunks
          : ["No extracted text preview is available for this source yet."]
      },
      async retry(id) {
        const conversationId = requireDocumentConversationId()
        const document = await apiClient.request<BackendDocumentRecord>(
          `/documents/${encodeURIComponent(id)}?conversationId=${encodeURIComponent(conversationId)}`,
        )
        return processAndIndexSource(mapBackendDocumentToSource(document))
      },
    },
    repositories: {
      async indexLocal(path) {
        const response =
          await apiClient.request<BackendRepositoryIndexResponse>(
            "/repos/index-local",
            {
              method: "POST",
              body: { path },
            },
          )
        return mapRepositoryIndexResult(response)
      },
      async indexVector(input) {
        const response =
          await apiClient.request<BackendRepositoryVectorIndexResponse>(
            "/repos/index-local/vector",
            {
              method: "POST",
              body: {
                path: input.path,
                conversationId: input.conversationId,
                conversationSettings: input.conversationSettings,
              },
            },
          )
        return mapRepositoryVectorIndexResult(response)
      },
      async ask(input) {
        const response = await apiClient.request<BackendRepositoryAskResponse>(
          "/repos/ask",
          {
            method: "POST",
            body: {
              repoName: input.repoName,
              question: input.question,
            },
          },
        )
        return mapRepositoryAskResult(response)
      },
      async searchVector(input) {
        const response =
          await apiClient.request<BackendRepositoryVectorSearchResponse>(
            "/repos/search-vector",
            {
              method: "POST",
              body: {
                conversationId: input.conversationId,
                query: input.query,
                repoName: input.repoName || undefined,
                topK: input.topK,
                conversationSettings: input.conversationSettings,
              },
            },
          )
        return mapRepositoryVectorSearchResult(response)
      },
    },
    diagnostics: {
      async getStatus() {
        return apiClient.request<DiagnosticsStatus>("/diagnostics/status")
      },
      async exportSupportBundle() {
        const bundle = await apiClient.request<Record<string, unknown>>(
          "/diagnostics/support-bundle",
        )
        return {
          filename: supportBundleFilename(),
          mediaType: "application/json" as const,
          content: JSON.stringify(bundle, null, 2),
        }
      },
    },
    profile: {
      capabilities: {
        avatarUpload: false,
        persistence: "local",
      },
      async load() {
        return { profile: await buildHttpProfile() }
      },
      async update(input) {
        saveLocalProfilePreferences(input)
        return {
          profile: await buildHttpProfile(),
          updatedAt: new Date().toISOString(),
        }
      },
      uploadAvatar: () =>
        Promise.reject(
          new AppError("Avatar upload is not supported by the backend yet.", {
            code: "server",
            status: 501,
          }),
        ),
      async exportData() {
        const profile = await buildHttpProfile()
        return {
          filename: "localchat-profile.json",
          mediaType: "application/json",
          content: JSON.stringify(
            {
              profile,
              support: {
                profilePreferences: "browser-local",
                avatarUpload: "unsupported",
                accountStatus: "backend",
              },
            },
            null,
            2,
          ),
        }
      },
    },
  }
}

interface BackendSessionResponse {
  username: string
}

interface BackendAccountStatusResponse {
  username: string
  api_key_configured: boolean
  api_key_active: boolean
}

type BackendCapabilitiesResponse = Parameters<typeof normalizeComponentCapabilities>[0]

interface BackendConversationDeleteResponse {
  deleted: boolean
  conversationId: string
}

interface BackendChatResponse {
  model: string
  answer: string
  ragUsed?: boolean
  ragWarnings?: string[]
  rerankingUsed?: boolean
  rerankerModel?: string | null
  rerankWarnings?: string[]
  compressionUsed?: boolean
  compressorMode?: string
  compressionWarnings?: string[]
  sources?: BackendChatSource[]
}

interface BackendChatSource {
  sourceNumber?: number
  documentId?: string
  documentName?: string
  chunkId?: string
  chunkIndex?: number
  score?: number
  vectorScore?: number
  rerankScore?: number | null
  finalRank?: number
  textPreview?: string
  pageNumber?: number | null
  collectionId?: string | null
}

interface BackendDocumentListResponse {
  conversationId: string
  documents: BackendDocumentRecord[]
}

interface BackendDocumentRecord {
  documentId?: string
  id?: string
  originalFilename?: string
  filename?: string
  mimeType?: string | null
  mediaType?: string | null
  size?: number
  createdAt?: string | null
  status?: string | null
  error?: string | null
  extractionWarnings?: unknown[]
}

interface BackendDocumentChunksResponse {
  chunks: Array<{ text?: unknown }>
}

interface BackendJobResponse {
  job: BackendJobRecord
}

interface BackendJobRecord {
  id: string
  state: "queued" | "running" | "succeeded" | "failed" | "cancel_requested" | "cancelled"
  progress: number
  message?: string | null
  result?: Record<string, unknown> | null
  error?: string | null
}

interface BackendRepositoryIndexResponse {
  repo_name: string
  indexed_files: number
  indexed_chunks: number
  freshness?: Record<string, unknown> | null
  warnings?: string[]
}

interface BackendRepositoryVectorIndexResponse
  extends BackendRepositoryIndexResponse {
  embedded_chunks: number
  conversationId: string
  collectionId: string
  embedderModel: string
  vectorDatabase: string
}

interface BackendRepositoryAskResponse {
  answer: string
  sources: string[]
  warnings?: string[]
  freshness?: Record<string, unknown> | null
}

interface BackendRepositoryVectorSearchResponse {
  query: string
  warnings?: string[]
  results: Array<Record<string, unknown>>
}

interface ParsedSseEvent {
  event: string
  data: unknown
}

function mapAccountStatus(response: BackendAccountStatusResponse) {
  return {
    username: response.username,
    apiKeyConfigured: response.api_key_configured,
    apiKeyActive: response.api_key_active,
  }
}

function mapRepositoryIndexResult(
  response: BackendRepositoryIndexResponse,
): RepositoryIndexResult {
  return {
    repoName: response.repo_name,
    indexedFiles: response.indexed_files,
    indexedChunks: response.indexed_chunks,
    freshness: mapRepositoryFreshness(response.freshness),
    warnings: response.warnings ?? [],
  }
}

function mapRepositoryVectorIndexResult(
  response: BackendRepositoryVectorIndexResponse,
): RepositoryVectorIndexResult {
  return {
    ...mapRepositoryIndexResult(response),
    embeddedChunks: response.embedded_chunks,
    conversationId: response.conversationId,
    collectionId: response.collectionId,
    embedderModel: response.embedderModel,
    vectorDatabase: response.vectorDatabase,
  }
}

function mapRepositoryAskResult(
  response: BackendRepositoryAskResponse,
): RepositoryAskResult {
  return {
    answer: response.answer,
    sources: response.sources,
    warnings: response.warnings ?? [],
    freshness: mapRepositoryFreshness(response.freshness),
  }
}

function mapRepositoryVectorSearchResult(
  response: BackendRepositoryVectorSearchResponse,
): RepositoryVectorSearchResult {
  return {
    query: response.query,
    warnings: response.warnings ?? [],
    results: response.results.map((result) => ({
      score: numberFromUnknown(result.score) ?? 0,
      repoName: stringFromUnknown(result.repoName) || undefined,
      filePath: stringFromUnknown(result.filePath) || undefined,
      startLine: numberFromUnknown(result.startLine) ?? undefined,
      endLine: numberFromUnknown(result.endLine) ?? undefined,
      language: stringFromUnknown(result.language) || undefined,
      symbolName: stringFromUnknown(result.symbolName) || undefined,
      symbolKind: stringFromUnknown(result.symbolKind) || undefined,
      text: stringFromUnknown(result.text),
    })),
  }
}

function supportBundleFilename(): string {
  return `localchat-support-bundle-${new Date().toISOString().slice(0, 10)}.json`
}

function mapRepositoryFreshness(value: unknown) {
  if (!value || typeof value !== "object") return undefined
  const candidate = value as Record<string, unknown>
  return {
    fresh: booleanFromUnknown(candidate.fresh),
    warnings: stringArrayFromUnknown(candidate.warnings),
  }
}

function createId(prefix: string): string {
  return `${prefix}-${globalThis.crypto?.randomUUID?.() ?? Date.now()}`
}

function mapBackendDocumentToSource(
  document: BackendDocumentRecord,
): SourceDocument {
  const warnings = Array.isArray(document.extractionWarnings)
    ? document.extractionWarnings.filter(
        (warning): warning is string => typeof warning === "string",
      )
    : []
  return {
    id: document.documentId ?? document.id ?? createId("source"),
    filename:
      stringFromUnknown(document.originalFilename) ||
      stringFromUnknown(document.filename) ||
      "Document",
    mediaType:
      stringFromUnknown(document.mimeType) ||
      stringFromUnknown(document.mediaType) ||
      "application/octet-stream",
    size: typeof document.size === "number" ? document.size : 0,
    createdAt: safeIsoDate(document.createdAt),
    status: mapDocumentStatus(document.status),
    summary: warnings.length > 0 ? warnings : undefined,
    error: stringFromUnknown(document.error) || undefined,
  }
}

function mapChatResponseMetadata(
  data: unknown,
): ChatMessageMetadata | undefined {
  if (!data || typeof data !== "object") return undefined
  const candidate = data as Record<string, unknown>
  const sources = Array.isArray(candidate.sources)
    ? candidate.sources.flatMap(mapChatSourceCitation)
    : []
  const metadata: ChatMessageMetadata = {
    model: stringFromUnknown(candidate.model) || undefined,
    ragUsed: booleanFromUnknown(candidate.ragUsed),
    ragWarnings: stringArrayFromUnknown(candidate.ragWarnings),
    rerankingUsed: booleanFromUnknown(candidate.rerankingUsed),
    rerankerModel: stringFromUnknown(candidate.rerankerModel) || null,
    rerankWarnings: stringArrayFromUnknown(candidate.rerankWarnings),
    compressionUsed: booleanFromUnknown(candidate.compressionUsed),
    compressorMode: stringFromUnknown(candidate.compressorMode) || undefined,
    compressionWarnings: stringArrayFromUnknown(candidate.compressionWarnings),
    sources,
  }
  return metadata
}

function mapChatSourceCitation(value: unknown): ChatSourceCitation[] {
  if (!value || typeof value !== "object") return []
  const candidate = value as Record<string, unknown>
  const sourceNumber = numberFromUnknown(candidate.sourceNumber)
  const finalRank = numberFromUnknown(candidate.finalRank)
  if (sourceNumber === null || finalRank === null) return []
  return [
    {
      sourceNumber,
      documentId: stringFromUnknown(candidate.documentId),
      documentName: stringFromUnknown(candidate.documentName) || "Document",
      chunkId: stringFromUnknown(candidate.chunkId),
      chunkIndex: numberFromUnknown(candidate.chunkIndex) ?? 0,
      score: numberFromUnknown(candidate.score) ?? 0,
      vectorScore: numberFromUnknown(candidate.vectorScore) ?? 0,
      rerankScore: numberFromUnknown(candidate.rerankScore),
      finalRank,
      textPreview: stringFromUnknown(candidate.textPreview),
      pageNumber: numberFromUnknown(candidate.pageNumber),
      collectionId: stringFromUnknown(candidate.collectionId) || null,
    },
  ]
}

function mapDocumentStatus(status: unknown): SourceDocumentStatus {
  if (status === "failed") return "failed"
  if (status === "indexed") return "ready"
  if (status === "processing") return "processing"
  if (status === "processed" || status === "uploaded") return "processing"
  return "processing"
}

function failedSourceFromJob(
  source: SourceDocument,
  job: BackendJobRecord,
): SourceDocument {
  return {
    ...source,
    status: "failed",
    error: job.error || job.message || "Document processing failed.",
  }
}

function isTerminalJobState(state: BackendJobRecord["state"]): boolean {
  return state === "succeeded" || state === "failed" || state === "cancelled"
}

function isBackendDocumentRecord(
  value: unknown,
): value is BackendDocumentRecord {
  return Boolean(value && typeof value === "object")
}

function delay(milliseconds: number): Promise<void> {
  return new Promise((resolve) => globalThis.setTimeout(resolve, milliseconds))
}

function uniqueStrings(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))]
}

function isProfilePreferences(
  value: unknown,
): value is UpdateProfileRequestDto {
  if (!value || typeof value !== "object") return false
  const candidate = value as Partial<UpdateProfileRequestDto>
  return (
    typeof candidate.displayName === "string" &&
    typeof candidate.handle === "string" &&
    typeof candidate.preferredName === "string" &&
    typeof candidate.role === "string" &&
    typeof candidate.about === "string" &&
    typeof candidate.preferredLanguage === "string" &&
    isResponsePreference(candidate.responsePreference)
  )
}

function isResponsePreference(value: unknown): value is ResponsePreference {
  return value === "concise" || value === "balanced" || value === "detailed"
}

function stringFromUnknown(value: unknown): string {
  return typeof value === "string" ? value : ""
}

function stringArrayFromUnknown(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : []
}

function booleanFromUnknown(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined
}

function numberFromUnknown(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function safeIsoDate(value: unknown): string {
  if (typeof value === "string" && !Number.isNaN(Date.parse(value))) {
    return value
  }
  return new Date().toISOString()
}

function resolveUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}/${path.replace(/^\//, "")}`
}

function parseSseFrames(buffer: string) {
  const normalized = buffer.replace(/\r\n/g, "\n")
  const frames = normalized.split(/\n\n/)
  return {
    frames: frames.slice(0, -1),
    remainder: frames.at(-1) ?? "",
  }
}

function parseSseFrame(frame: string): ParsedSseEvent {
  let event = "message"
  const dataLines: string[] = []
  for (const line of frame.split(/\n/)) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim()
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart())
    }
  }
  const dataText = dataLines.join("\n")
  if (!dataText) return { event, data: null }
  try {
    return { event, data: JSON.parse(dataText) as unknown }
  } catch {
    return { event, data: dataText }
  }
}

function sseText(data: unknown, key: string): string {
  if (!data || typeof data !== "object") return ""
  const value = (data as Record<string, unknown>)[key]
  return typeof value === "string" ? value : ""
}

function sseNumber(data: unknown, key: string): number | undefined {
  if (!data || typeof data !== "object") return undefined
  const value = (data as Record<string, unknown>)[key]
  return typeof value === "number" ? value : undefined
}

async function responseError(response: Response): Promise<AppError> {
  const text = await response.text().catch(() => "")
  try {
    const data = text ? JSON.parse(text) as Record<string, unknown> : null
    const detail = data?.detail
    return new AppError(
      typeof detail === "string"
        ? detail
        : typeof data?.message === "string"
          ? data.message
          : `Request failed with status ${response.status}.`,
      {
        status: response.status,
        code: response.status >= 500 ? "server" : "unknown",
      },
    )
  } catch {
    return new AppError(
      text || `Request failed with status ${response.status}.`,
      {
        status: response.status,
        code: response.status >= 500 ? "server" : "unknown",
      },
    )
  }
}

function readCookie(name: string): string {
  if (typeof document === "undefined" || !document.cookie) return ""
  const value = document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`))
    ?.slice(name.length + 1)
  return value ? decodeURIComponent(value) : ""
}
