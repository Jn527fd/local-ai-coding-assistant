import type {
  AttachmentStatus,
  ChatAttachment,
  ChatMessage,
  ChatSourceCitation,
  Conversation,
  ConversationSummary,
  MessageRole,
  MessageStatus,
  ModelConfiguration,
} from "../../domain/models"
import type { CreateConversationRequestDto } from "../../domain/dtos"
import { createDefaultModelConfiguration } from "../../domain/defaults"

export interface BackendConversationListResponse {
  conversations: BackendConversationRecord[]
}

export interface BackendConversationResponse {
  conversation: BackendConversationRecord
}

export interface BackendConversationRecord {
  id: string
  title?: string
  messages?: unknown[]
  settings?: Partial<BackendConversationSettings>
  metadata?: Record<string, unknown>
  attachmentReferences?: unknown[]
  createdAt?: string | null
  updatedAt?: string | null
}

export interface BackendConversationSettings {
  llmModel?: string | null
  embedderModel?: string | null
  embedder?: string | null
  ocrEngine?: string | null
  pdfParser?: string | null
  chunker?: string | null
  vectorDatabase?: string | null
  ragPipeline?: string | null
  reranker?: string | null
  contextCompressor?: string | null
  visionModel?: string | null
}

interface FrontendConversationMetadata {
  systemPrompt?: string
  sourceIds?: string[]
  temporary?: boolean
}

export function createLocalConversation(
  input: CreateConversationRequestDto,
): Conversation {
  const createdAt = new Date().toISOString()
  return {
    id: createId("conversation"),
    title: input.title?.trim() || "New conversation",
    createdAt,
    updatedAt: createdAt,
    messages: [],
    systemPrompt: input.systemPrompt,
    modelConfiguration: { ...input.modelConfiguration },
    sourceIds: [...input.sourceIds],
    temporary: input.temporary,
  }
}

export function mapBackendConversationToConversation(
  record: BackendConversationRecord,
): Conversation {
  const metadata = readFrontendMetadata(record.metadata)
  const createdAt = safeIsoDate(record.createdAt ?? record.updatedAt)
  const updatedAt = safeIsoDate(record.updatedAt ?? record.createdAt)
  const fallbackConfiguration = createDefaultModelConfiguration()
  const modelConfiguration = mapBackendSettings(
    record.settings,
    fallbackConfiguration,
  )
  return {
    id: record.id,
    title: record.title?.trim() || "Untitled thread",
    createdAt,
    updatedAt,
    messages: mapBackendMessages(record.id, record.messages),
    systemPrompt:
      metadata.systemPrompt ??
      stringFromRecordMetadata(record.metadata, "systemPrompt") ??
      "",
    modelConfiguration,
    sourceIds:
      metadata.sourceIds ??
      sourceIdsFromMetadata(record.metadata) ??
      sourceIdsFromAttachmentReferences(record.attachmentReferences),
    temporary:
      metadata.temporary ??
      booleanFromRecordMetadata(record.metadata, "temporary") ??
      false,
  }
}

export function mapConversationToBackendRecord(
  conversation: Conversation,
  existingRecord: BackendConversationRecord | null = null,
): BackendConversationRecord {
  return {
    id: conversation.id,
    title: conversation.title,
    messages: conversation.messages.map(mapMessageToBackendMessage),
    settings: mapConfigurationToBackendSettings(
      conversation.modelConfiguration,
    ),
    metadata: {
      ...(existingRecord?.metadata ?? {}),
      frontend: {
        systemPrompt: conversation.systemPrompt,
        sourceIds: conversation.sourceIds,
        temporary: conversation.temporary,
      },
    },
    attachmentReferences: attachmentReferencesFromConversation(conversation),
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
  }
}

export function toConversationSummary(
  conversation: Conversation,
): ConversationSummary {
  return {
    id: conversation.id,
    title: conversation.title,
    createdAt: conversation.createdAt,
    updatedAt: conversation.updatedAt,
    temporary: conversation.temporary,
  }
}

export function cloneConversation(conversation: Conversation): Conversation {
  return structuredClone(conversation)
}

export function mapConfigurationToBackendSettings(
  configuration: ModelConfiguration,
): BackendConversationSettings {
  return {
    llmModel: configuration.llmModel,
    visionModel: configuration.visionModel,
    embedderModel: configuration.embedder,
    ocrEngine: configuration.ocrEngine,
    pdfParser: configuration.pdfParser,
    chunker: configuration.chunker,
    vectorDatabase: configuration.vectorDatabase,
    ragPipeline: configuration.ragPipeline,
    contextCompressor: configuration.contextCompressor,
    reranker: configuration.reranker,
  }
}

function mapBackendSettings(
  settings: Partial<BackendConversationSettings> | undefined,
  fallback: ModelConfiguration,
): ModelConfiguration {
  const mapped: ModelConfiguration = {
    ...fallback,
    llmModel: nonEmpty(settings?.llmModel) ?? fallback.llmModel,
    visionModel: nonEmpty(settings?.visionModel) ?? fallback.visionModel,
    embedder:
      nonEmpty(settings?.embedderModel) ??
      nonEmpty(settings?.embedder) ??
      fallback.embedder,
    ocrEngine: nonEmpty(settings?.ocrEngine) ?? fallback.ocrEngine,
    pdfParser: nonEmpty(settings?.pdfParser) ?? fallback.pdfParser,
    vectorDatabase:
      nonEmpty(settings?.vectorDatabase) ?? fallback.vectorDatabase,
    contextCompressor:
      nonEmpty(settings?.contextCompressor) ?? fallback.contextCompressor,
    reranker: nonEmpty(settings?.reranker) ?? fallback.reranker,
  }
  const chunker = nonEmpty(settings?.chunker)
  const ragPipeline = nonEmpty(settings?.ragPipeline)
  if (chunker) mapped.chunker = chunker
  if (ragPipeline) mapped.ragPipeline = ragPipeline
  return mapped
}

function mapBackendMessages(
  conversationId: string,
  messages: unknown[] | undefined,
): ChatMessage[] {
  return (messages ?? []).flatMap((message, index) => {
    if (!message || typeof message !== "object") return []
    const candidate = message as Record<string, unknown>
    const role = normalizeRole(candidate.role)
    const content = nonEmpty(candidate.content)
    if (!role || !content) return []
    return [
      {
        id: nonEmpty(candidate.id) ?? `${conversationId}-message-${index}`,
        conversationId: nonEmpty(candidate.conversationId) ?? conversationId,
        role,
        content,
        status: normalizeMessageStatus(candidate.status),
        createdAt: safeIsoDate(candidate.createdAt),
        attachments: normalizeAttachments(candidate.attachments),
        error: nonEmpty(candidate.error),
        metadata: normalizeMessageMetadata(candidate.metadata),
      },
    ]
  })
}

function mapMessageToBackendMessage(message: ChatMessage) {
  return {
    id: message.id,
    conversationId: message.conversationId,
    role: message.role,
    content: message.content,
    status: message.status,
    createdAt: message.createdAt,
    attachments: message.attachments,
    error: message.error,
    metadata: message.metadata,
  }
}

function normalizeMessageMetadata(value: unknown): ChatMessage["metadata"] {
  if (!value || typeof value !== "object") return undefined
  const candidate = value as Record<string, unknown>
  return {
    model: nonEmpty(candidate.model),
    ragUsed: booleanOrUndefined(candidate.ragUsed),
    ragWarnings: stringArray(candidate.ragWarnings) ?? [],
    rerankingUsed: booleanOrUndefined(candidate.rerankingUsed),
    rerankerModel: nonEmpty(candidate.rerankerModel) ?? null,
    rerankWarnings: stringArray(candidate.rerankWarnings) ?? [],
    compressionUsed: booleanOrUndefined(candidate.compressionUsed),
    compressorMode: nonEmpty(candidate.compressorMode),
    compressionWarnings: stringArray(candidate.compressionWarnings) ?? [],
    sources: normalizeSourceCitations(candidate.sources),
  }
}

function normalizeSourceCitations(value: unknown): ChatSourceCitation[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((source) => {
    if (!source || typeof source !== "object") return []
    const candidate = source as Record<string, unknown>
    const sourceNumber = numberOrNull(candidate.sourceNumber)
    const finalRank = numberOrNull(candidate.finalRank)
    if (sourceNumber === null || finalRank === null) return []
    return [
      {
        sourceNumber,
        documentId: nonEmpty(candidate.documentId) ?? "",
        documentName: nonEmpty(candidate.documentName) ?? "Document",
        chunkId: nonEmpty(candidate.chunkId) ?? "",
        chunkIndex: numberOrNull(candidate.chunkIndex) ?? 0,
        score: numberOrNull(candidate.score) ?? 0,
        vectorScore: numberOrNull(candidate.vectorScore) ?? 0,
        rerankScore: numberOrNull(candidate.rerankScore),
        finalRank,
        textPreview: nonEmpty(candidate.textPreview) ?? "",
        pageNumber: numberOrNull(candidate.pageNumber),
        collectionId: nonEmpty(candidate.collectionId) ?? null,
      },
    ]
  })
}

function normalizeAttachments(value: unknown): ChatAttachment[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((attachment, index) => {
    if (!attachment || typeof attachment !== "object") return []
    const candidate = attachment as Record<string, unknown>
    const filename =
      nonEmpty(candidate.filename) ??
      nonEmpty(candidate.name) ??
      `attachment-${index + 1}`
    return [
      {
        id:
          nonEmpty(candidate.id) ??
          nonEmpty(candidate.documentId) ??
          `attachment-${index + 1}`,
        filename,
        mediaType:
          nonEmpty(candidate.mediaType) ??
          nonEmpty(candidate.type) ??
          "application/octet-stream",
        size: numberOrZero(candidate.size),
        status: normalizeAttachmentStatus(candidate.status),
        url: nonEmpty(candidate.url),
        error: nonEmpty(candidate.error),
      },
    ]
  })
}

function attachmentReferencesFromConversation(conversation: Conversation) {
  const references = new Map<string, unknown>()
  conversation.sourceIds.forEach((sourceId) => {
    references.set(sourceId, { documentId: sourceId, source: "sourceIds" })
  })
  conversation.messages.forEach((message) => {
    message.attachments.forEach((attachment) => {
      references.set(attachment.id, {
        id: attachment.id,
        name: attachment.filename,
        mediaType: attachment.mediaType,
        size: attachment.size,
        status: attachment.status,
      })
    })
  })
  return [...references.values()]
}

function readFrontendMetadata(
  metadata: Record<string, unknown> | undefined,
): FrontendConversationMetadata {
  const value = metadata?.frontend ?? metadata?.proposedFrontend
  if (!value || typeof value !== "object") return {}
  const candidate = value as Record<string, unknown>
  return {
    systemPrompt: nonEmpty(candidate.systemPrompt),
    sourceIds: stringArray(candidate.sourceIds),
    temporary:
      typeof candidate.temporary === "boolean"
        ? candidate.temporary
        : undefined,
  }
}

function sourceIdsFromMetadata(
  metadata: Record<string, unknown> | undefined,
): string[] | undefined {
  return (
    stringArray(metadata?.sourceIds) ??
    stringArray(metadata?.documentIds) ??
    stringArray(metadata?.attachmentDocumentIds)
  )
}

function sourceIdsFromAttachmentReferences(
  references: unknown[] | undefined,
): string[] {
  if (!Array.isArray(references)) return []
  const ids = references
    .map((reference) => {
      if (!reference || typeof reference !== "object") return ""
      const candidate = reference as Record<string, unknown>
      return (
        nonEmpty(candidate.documentId) ??
        nonEmpty(candidate.sourceId) ??
        nonEmpty(candidate.id) ??
        ""
      )
    })
    .filter(Boolean)
  return [...new Set(ids)]
}

function stringFromRecordMetadata(
  metadata: Record<string, unknown> | undefined,
  key: string,
) {
  return nonEmpty(metadata?.[key])
}

function booleanFromRecordMetadata(
  metadata: Record<string, unknown> | undefined,
  key: string,
) {
  return typeof metadata?.[key] === "boolean" ? metadata[key] : undefined
}

function normalizeRole(value: unknown): MessageRole | null {
  return value === "user" || value === "assistant" || value === "system"
    ? value
    : null
}

function normalizeMessageStatus(value: unknown): MessageStatus {
  return value === "pending" ||
    value === "streaming" ||
    value === "complete" ||
    value === "stopped" ||
    value === "failed"
    ? value
    : "complete"
}

function normalizeAttachmentStatus(value: unknown): AttachmentStatus {
  return value === "uploading" || value === "ready" || value === "failed"
    ? value
    : "ready"
}

function nonEmpty(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined
}

function stringArray(value: unknown): string[] | undefined {
  if (!Array.isArray(value)) return undefined
  return value.filter((item): item is string => typeof item === "string")
}

function numberOrZero(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0
}

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function booleanOrUndefined(value: unknown): boolean | undefined {
  return typeof value === "boolean" ? value : undefined
}

function safeIsoDate(value: unknown): string {
  if (typeof value === "string" && !Number.isNaN(Date.parse(value))) {
    return value
  }
  return new Date().toISOString()
}

function createId(prefix: string): string {
  return `${prefix}-${globalThis.crypto?.randomUUID?.() ?? Date.now()}`
}
