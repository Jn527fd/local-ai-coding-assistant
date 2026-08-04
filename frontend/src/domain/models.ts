export type MessageRole = "user" | "assistant" | "system"

export type MessageStatus = "pending" | "streaming" | "complete" | "stopped" | "failed"

export type AttachmentStatus = "uploading" | "ready" | "failed"

export interface ChatAttachment {
  id: string
  filename: string
  mediaType: string
  size: number
  status: AttachmentStatus
  url?: string
  error?: string
}

export interface ChatMessage {
  id: string
  conversationId: string
  role: MessageRole
  content: string
  status: MessageStatus
  createdAt: string
  attachments: ChatAttachment[]
  error?: string
  metadata?: ChatMessageMetadata
}

export interface ChatMessageMetadata {
  model?: string
  ragUsed?: boolean
  ragWarnings?: string[]
  rerankingUsed?: boolean
  rerankerModel?: string | null
  rerankWarnings?: string[]
  compressionUsed?: boolean
  compressorMode?: string
  compressionWarnings?: string[]
  sources?: ChatSourceCitation[]
}

export interface ChatSourceCitation {
  sourceNumber: number
  documentId: string
  documentName: string
  chunkId: string
  chunkIndex: number
  score: number
  vectorScore: number
  rerankScore?: number | null
  finalRank: number
  textPreview: string
  pageNumber?: number | null
  collectionId?: string | null
}

export interface ModelConfiguration {
  llmModel: string
  visionModel: string
  embedder?: string
  pdfParser?: string
  chunker?: string
  vectorDatabase?: string
  ragPipeline?: string
  ocrEngine?: string
  contextCompressor?: string
  reranker?: string
}

export interface Conversation {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: ChatMessage[]
  systemPrompt: string
  modelConfiguration: ModelConfiguration
  sourceIds: string[]
  temporary: boolean
}

export interface ConversationSummary {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  temporary: boolean
}

export type SourceDocumentStatus = "uploading" | "processing" | "ready" | "failed"

export interface SourceDocument {
  id: string
  filename: string
  mediaType: string
  size: number
  createdAt: string
  status: SourceDocumentStatus
  summary?: string[]
  error?: string
}

export interface ConversationDraftConfiguration {
  systemPrompt: string
  modelConfiguration: ModelConfiguration
  sourceIds: string[]
  temporary: boolean
}

export interface AuthUser {
  id: string
  username: string
  email: string
  displayName: string
}

export interface AuthSession {
  accessToken: string
  expiresAt: string
  user: AuthUser
}

export interface AccountStatus {
  username: string
  apiKeyConfigured: boolean
  apiKeyActive: boolean
}

export interface ComponentCapability {
  id: string
  label: string
  type: string
  available: boolean
  source: string
  name?: string
  size?: number | null
  modifiedAt?: string | null
  details?: Record<string, unknown>
  implementationStatus?: string
  implemented?: boolean
  execution?: {
    status?: string
    implemented?: boolean
    mode?: string
    description?: string
  }
}

export interface ComponentCapabilities {
  llmModels: ComponentCapability[]
  embedderModels: ComponentCapability[]
  rerankerModels: ComponentCapability[]
  visionModels: ComponentCapability[]
  ocrEngines: ComponentCapability[]
  pdfParsers: ComponentCapability[]
  chunkers: ComponentCapability[]
  vectorDatabases: ComponentCapability[]
  ragPipelines: ComponentCapability[]
  contextCompressors: ComponentCapability[]
  unknownOllamaModels: ComponentCapability[]
}

export type ResponsePreference = "concise" | "balanced" | "detailed"

export interface UserProfile {
  id: string
  displayName: string
  handle: string
  preferredName: string
  avatarUrl: string | null
  role: string
  about: string
  preferredLanguage: string
  responsePreference: ResponsePreference
  accountType: "member" | "admin"
  deviceName: string
  joinedAt: string
  storageLocation: string
}

export interface Page<Result> {
  items: Result[]
  nextCursor: string | null
  total: number
}

export type OAuthProvider = "google" | "company"

export interface OAuthRedirect {
  provider: OAuthProvider
  url: string
}
