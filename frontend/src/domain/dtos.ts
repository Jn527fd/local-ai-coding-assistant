import type {
  ChatAttachment,
  MessageRole,
  MessageStatus,
  ModelConfiguration,
  ResponsePreference,
  SourceDocumentStatus,
  UserProfile,
} from "./models"

export interface SignInRequest {
  username: string
  password: string
}

export interface VerifyEmailCodeRequest {
  email: string
  code: string
}

export interface CreateAccountRequest {
  email: string
  password: string
}

export interface CreateConversationRequestDto {
  title?: string
  systemPrompt: string
  modelConfiguration: ModelConfiguration
  sourceIds: string[]
  temporary: boolean
}

export interface RenameConversationRequestDto {
  title: string
}

export interface UpdateConversationConfigurationRequestDto {
  systemPrompt?: string
  modelConfiguration?: Partial<ModelConfiguration>
  sourceIds?: string[]
  temporary?: boolean
}

export interface SendMessageRequestDto {
  conversationId: string
  content: string
  attachmentIds: string[]
  attachments?: ChatAttachment[]
}

export interface ListConversationsRequestDto {
  cursor?: string | null
  limit?: number
}

export interface ChatMessageResponseDto {
  id: string
  conversationId: string
  role: MessageRole
  content: string
  status: MessageStatus
  createdAt: string
  attachments: ChatAttachment[]
  error?: string
}

export interface ConversationResponseDto {
  id: string
  title: string
  createdAt: string
  updatedAt: string
  messages: ChatMessageResponseDto[]
  systemPrompt: string
  modelConfiguration: ModelConfiguration
  sourceIds: string[]
  temporary: boolean
}

export interface SourceDocumentResponseDto {
  id: string
  filename: string
  mediaType: string
  size: number
  createdAt: string
  status: SourceDocumentStatus
  summary?: string[]
  error?: string
}

export interface LoadProfileRequestDto {
  includeAvatar?: boolean
}

export interface LoadProfileResponseDto {
  profile: UserProfile
}

export interface UpdateProfileRequestDto {
  displayName: string
  handle: string
  preferredName: string
  role: string
  about: string
  preferredLanguage: string
  responsePreference: ResponsePreference
}

export interface UpdateProfileResponseDto {
  profile: UserProfile
  updatedAt: string
}

export interface UploadProfileAvatarResponseDto {
  avatarUrl: string
}

export interface ExportProfileResponseDto {
  filename: string
  mediaType: "application/json"
  content: string
}
