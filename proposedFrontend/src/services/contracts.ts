import type {
  AuthSession,
  AccountStatus,
  ChatMessage,
  ComponentCapabilities,
  Conversation,
  ConversationSummary,
  OAuthProvider,
  OAuthRedirect,
  Page,
  SourceDocument,
} from "../domain/models"
import type {
  CreateAccountRequest,
  CreateConversationRequestDto,
  ExportProfileResponseDto,
  ListConversationsRequestDto,
  LoadProfileRequestDto,
  LoadProfileResponseDto,
  SendMessageRequestDto,
  SignInRequest,
  UpdateProfileRequestDto,
  UpdateProfileResponseDto,
  UpdateConversationConfigurationRequestDto,
  UploadProfileAvatarResponseDto,
  VerifyEmailCodeRequest,
} from "../domain/dtos"

export interface AuthService {
  signIn(input: SignInRequest): Promise<AuthSession>
  signOut(): Promise<void>
  restoreSession(): Promise<AuthSession | null>
  requestEmailVerification(email: string): Promise<void>
  verifyEmailCode(input: VerifyEmailCodeRequest): Promise<void>
  createAccount(input: CreateAccountRequest): Promise<AuthSession>
  getOAuthRedirect(
    provider: OAuthProvider,
    returnTo: string,
  ): Promise<OAuthRedirect>
}

export interface AccountService {
  getStoredApiKey(): string
  setStoredApiKey(apiKey: string): void
  getStatus(apiKey?: string): Promise<AccountStatus>
  updateApiKey(apiKey: string): Promise<AccountStatus>
}

export interface CapabilityService {
  list(): Promise<ComponentCapabilities>
}

export interface ConversationService {
  list(input?: ListConversationsRequestDto): Promise<Page<ConversationSummary>>
  get(id: string): Promise<Conversation>
  create(input: CreateConversationRequestDto): Promise<Conversation>
  rename(id: string, title: string): Promise<ConversationSummary>
  delete(id: string): Promise<void>
  updateConfiguration(
    id: string,
    input: UpdateConversationConfigurationRequestDto,
  ): Promise<Conversation>
}

export interface MessageService {
  send(input: SendMessageRequestDto): Promise<ChatMessage>
  stream(input: SendMessageRequestDto): AsyncIterable<MessageStreamEvent>
  cancel(conversationId: string, messageId: string): Promise<void>
  retry(conversationId: string, messageId: string): Promise<ChatMessage>
}

export interface SourceService {
  list(): Promise<SourceDocument[]>
  upload(files: File[]): Promise<SourceDocument[]>
  delete(id: string): Promise<void>
  getSummary(id: string): Promise<string[]>
  retry(id: string): Promise<SourceDocument>
}

export interface ProfileService {
  capabilities?: {
    avatarUpload: boolean
    persistence: "backend" | "local"
  }
  load(input?: LoadProfileRequestDto): Promise<LoadProfileResponseDto>
  update(input: UpdateProfileRequestDto): Promise<UpdateProfileResponseDto>
  uploadAvatar(file: File): Promise<UploadProfileAvatarResponseDto>
  exportData(): Promise<ExportProfileResponseDto>
}

export interface RepositoryService {
  indexLocal(path: string): Promise<RepositoryIndexResult>
  indexVector(
    input: RepositoryVectorIndexRequest,
  ): Promise<RepositoryVectorIndexResult>
  ask(input: RepositoryAskRequest): Promise<RepositoryAskResult>
  searchVector(
    input: RepositoryVectorSearchRequest,
  ): Promise<RepositoryVectorSearchResult>
}

export interface DiagnosticsService {
  getStatus(): Promise<DiagnosticsStatus>
  exportSupportBundle(): Promise<DiagnosticsExport>
}

export interface DiagnosticsStatus {
  runtime?: DiagnosticsSection
  models?: DiagnosticsSection
  documents?: DiagnosticsSection
  retrieval?: DiagnosticsSection
  jobs?: DiagnosticsSection
  warnings?: string[]
  generatedAt?: string
}

export interface DiagnosticsExport {
  filename: string
  mediaType: "application/json"
  content: string
}

export type DiagnosticsSection = Record<string, unknown>

export interface RepositoryIndexResult {
  repoName: string
  indexedFiles: number
  indexedChunks: number
  freshness?: RepositoryFreshness
  warnings: string[]
}

export interface RepositoryVectorIndexRequest {
  path: string
  conversationId: string
  conversationSettings?: Record<string, unknown>
}

export interface RepositoryVectorIndexResult extends RepositoryIndexResult {
  embeddedChunks: number
  conversationId: string
  collectionId: string
  embedderModel: string
  vectorDatabase: string
}

export interface RepositoryAskRequest {
  repoName: string
  question: string
}

export interface RepositoryAskResult {
  answer: string
  sources: string[]
  warnings: string[]
  freshness?: RepositoryFreshness
}

export interface RepositoryVectorSearchRequest {
  conversationId: string
  query: string
  repoName?: string
  topK?: number
  conversationSettings?: Record<string, unknown>
}

export interface RepositoryVectorSearchResult {
  query: string
  warnings: string[]
  results: RepositoryVectorSearchHit[]
}

export interface RepositoryVectorSearchHit {
  score: number
  repoName?: string
  filePath?: string
  startLine?: number
  endLine?: number
  language?: string
  symbolName?: string
  symbolKind?: string
  text: string
}

export interface RepositoryFreshness {
  fresh?: boolean
  warnings?: string[]
}

export interface MessageAcceptedEvent {
  type: "accepted"
  userMessage: ChatMessage
  assistantMessage: ChatMessage
}

export interface MessageDeltaEvent {
  type: "delta"
  messageId: string
  delta: string
}

export interface MessageCompleteEvent {
  type: "complete"
  message: ChatMessage
}

export interface MessageFailedEvent {
  type: "failed"
  message: ChatMessage
}

export type MessageStreamEvent = MessageAcceptedEvent | MessageDeltaEvent | MessageCompleteEvent | MessageFailedEvent

export interface AppServices {
  auth: AuthService
  account: AccountService
  capabilities: CapabilityService
  conversations: ConversationService
  messages: MessageService
  sources: SourceService
  repositories: RepositoryService
  diagnostics: DiagnosticsService
  profile: ProfileService
}
