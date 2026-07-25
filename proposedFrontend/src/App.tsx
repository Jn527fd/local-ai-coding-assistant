import {
  useEffect,
  useMemo,
  useState,
  useRef,
  type CSSProperties,
  type ChangeEvent,
  type FormEvent,
  type PointerEvent,
} from "react"
import { useLocation, useNavigate, useParams } from "react-router-dom"
import { useAuth } from "./auth/AuthProvider"
import { SourcesModal } from "./features/sources/SourcesModal"
import { ChatTranscript } from "./features/chat/ChatTranscript"
import {
  ChatComposer,
  type ComposerAttachmentDraft,
} from "./features/chat/ChatComposer"
import type {
  Conversation,
  ConversationDraftConfiguration,
  ChatMessage,
  ComponentCapabilities,
  ModelConfiguration,
  SourceDocument,
} from "./domain/models"
import {
  createDefaultConversationDraft,
  createDefaultModelConfiguration,
} from "./domain/defaults"
import { appServices } from "./services"
import { createConfigurationFromCapabilities } from "./services/capabilities"
import { normalizeError, validationError } from "./services/errors"
import {
  errorAsyncState,
  idleAsyncState,
  pendingAsyncState,
  successAsyncState,
  type AsyncState,
} from "./services/asyncState"
import { DeleteConversationModal } from "./features/conversations/DeleteConversationModal"
import { SearchChatsModal } from "./features/conversations/SearchChatsModal"
import { RecentChatsPopover } from "./features/conversations/RecentChatsPopover"
import {
  ConversationSidebar,
  ProfileMenu,
} from "./features/conversations/ConversationSidebar"
import { RightConfigurationToolbar } from "./features/configuration/RightConfigurationToolbar"
import { ChatConfigurationModal } from "./features/configuration/ChatConfigurationModal"
import { SystemPromptModal } from "./features/configuration/SystemPromptModal"
import {
  ConfirmationModal,
  type ConfirmationRequest,
} from "./components/ConfirmationModal"
import {
  applyAppSettings,
  loadAppSettings,
  SETTINGS_CHANGED_EVENT,
  type AppSettings,
} from "./features/settings/settingsStorage"

const initialConversations: Conversation[] = []

interface ConversationListResult {
  nextCursor: string | null
  total: number
}

interface MessageSendResult {
  key: string
  conversationId?: string
  assistantMessageId?: string
}

export default function App() {
  const auth = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const { conversationId: routeConversationId } = useParams()
  const [profileMenuOpen, setProfileMenuOpen] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [liveSettings, setLiveSettings] = useState<AppSettings>(() =>
    loadAppSettings(),
  )
  const [sidebarProfileName, setSidebarProfileName] = useState(
    auth.session?.user.displayName ?? "User",
  )
  const [sidebarProfileId, setSidebarProfileId] = useState(
    auth.session?.user.id ?? "user-local",
  )
  const [sidebarProfileAvatarUrl, setSidebarProfileAvatarUrl] =
    useState<string | null>(null)
  const [composerDrafts, setComposerDrafts] = useState<Record<string, string>>(
    {},
  )
  const [attachmentDrafts, setAttachmentDrafts] =
    useState<Record<string, ComposerAttachmentDraft[]>>({})
  const [attachmentErrors, setAttachmentErrors] =
    useState<Record<string, string>>({})
  const [messageSendState, setMessageSendState] =
    useState<AsyncState<MessageSendResult>>(() => idleAsyncState())
  const [conversations, setConversations] = useState<Conversation[]>(
    () => initialConversations,
  )
  const [serviceStateLoaded, setServiceStateLoaded] = useState(false)
  const [conversationListState, setConversationListState] =
    useState<AsyncState<ConversationListResult>>(() =>
      pendingAsyncState({ nextCursor: null, total: 0 }),
    )
  const [activeConversationId, setActiveConversationId] =
    useState<string | null>(null)
  const [editingConversationId, setEditingConversationId] =
    useState<string | null>(null)
  const [editingConversationTitle, setEditingConversationTitle] = useState("")
  const [renameState, setRenameState] = useState<AsyncState<{
    conversationId: string
  }>>(() => idleAsyncState())
  const [pendingDeleteConversationId, setPendingDeleteConversationId] =
    useState<string | null>(null)
  const [deleteConversationState, setDeleteConversationState] =
    useState<AsyncState<{ conversationId: string }>>(() => idleAsyncState())
  const [conversationDraft, setConversationDraft] =
    useState<ConversationDraftConfiguration>(createDefaultConversationDraft)
  const [capabilityState, setCapabilityState] =
    useState<AsyncState<ComponentCapabilities>>(() => idleAsyncState())
  const [activeRight, setActiveRight] = useState<string | null>(null)
  const [searchValue, setSearchValue] = useState("")
  const [searchOpen, setSearchOpen] = useState(false)
  const [contextOpen, setContextOpen] = useState(false)
  const [draftSystemPrompt, setDraftSystemPrompt] = useState("")
  const [promptSaveState, setPromptSaveState] = useState<AsyncState<string>>(
    () => idleAsyncState(),
  )
  const [configurationSaveState, setConfigurationSaveState] =
    useState<AsyncState<ConversationDraftConfiguration>>(() => idleAsyncState())
  const [modelFileName, setModelFileName] = useState<string | null>(null)
  const [modelFileError, setModelFileError] = useState("")
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [sourceSearch, setSourceSearch] = useState("")
  const [sourceDocuments, setSourceDocuments] = useState<SourceDocument[]>([])
  const [sourceUploadProgress, setSourceUploadProgress] = useState(0)
  const [sourceUploadState, setSourceUploadState] =
    useState<AsyncState<SourceDocument[]>>(() => idleAsyncState())
  const [summarySourceId, setSummarySourceId] = useState<string | null>(null)
  const [newChatNoticeOpen, setNewChatNoticeOpen] = useState(false)
  const [recentsOpen, setRecentsOpen] = useState(false)
  const [hovering, setHovering] = useState(false)
  const [cursor, setCursor] = useState({ x: 0, y: 0 })
  const [confirmationRequest, setConfirmationRequest] =
    useState<ConfirmationRequest | null>(null)
  const [confirmationState, setConfirmationState] = useState<AsyncState<void>>(
    () => idleAsyncState(),
  )
  const fileRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const syncSettings = () => {
      const nextSettings = loadAppSettings()
      setLiveSettings(nextSettings)
      applyAppSettings(nextSettings)
    }

    syncSettings()
    window.addEventListener(SETTINGS_CHANGED_EVENT, syncSettings)
    window.addEventListener("storage", syncSettings)

    return () => {
      window.removeEventListener(SETTINGS_CHANGED_EVENT, syncSettings)
      window.removeEventListener("storage", syncSettings)
    }
  }, [])

  useEffect(() => {
    let active = true
    setCapabilityState(pendingAsyncState())
    appServices.capabilities
      .list()
      .then((nextCapabilities) => {
        if (!active) return
        setCapabilityState(successAsyncState(nextCapabilities))
      })
      .catch((error) => {
        if (!active) return
        setCapabilityState(errorAsyncState(normalizeError(error)))
      })
    return () => {
      active = false
    }
  }, [])

  const searchInputRef = useRef<HTMLInputElement>(null)
  const composerInputRef = useRef<HTMLTextAreaElement>(null)
  const deleteCancelButtonRef = useRef<HTMLButtonElement>(null)
  const searchButtonRef = useRef<HTMLButtonElement>(null)
  const recentsButtonRef = useRef<HTMLButtonElement>(null)
  const profileButtonRef = useRef<HTMLButtonElement>(null)
  const contextButtonRef = useRef<HTMLButtonElement>(null)
  const systemPromptRef = useRef<HTMLTextAreaElement>(null)
  const modelFileRef = useRef<HTMLInputElement>(null)
  const sourcesButtonRef = useRef<HTMLButtonElement>(null)
  const sourcesSearchRef = useRef<HTMLInputElement>(null)
  const chatConfigButtonRef = useRef<HTMLButtonElement>(null)
  const llmModelSelectRef = useRef<HTMLSelectElement>(null)
  const newChatNoticeTimerRef = useRef<number | null>(null)
  const confirmationCancelRef = useRef<HTMLButtonElement>(null)
  const attachmentTimersRef = useRef(new Map<string, number>())
  const attachmentUrlsRef = useRef(new Set<string>())

  const activeConversation = conversations.find(
    (conversation) => conversation.id === activeConversationId,
  )
  const composerKey = activeConversationId ?? "new-conversation"
  const inputValue = composerDrafts[composerKey] ?? ""
  const composerAttachments = attachmentDrafts[composerKey] ?? []
  const attachmentError = attachmentErrors[composerKey] ?? ""
  const isSending = messageSendState.status === "pending"
  const messageError = messageSendState.error?.message ?? ""
  const conversationListLoading = conversationListState.status === "pending"
  const conversationListError = conversationListState.error?.message ?? ""
  const conversationNextCursor = conversationListState.data?.nextCursor ?? null
  const conversationListTotal = conversationListState.data?.total ?? 0
  const renamingConversationId =
    renameState.status === "pending"
      ? (renameState.data?.conversationId ?? null)
      : null
  const conversationActionError = renameState.error?.message ?? ""
  const isDeletingConversation = deleteConversationState.status === "pending"
  const deleteConversationError = deleteConversationState.error?.message ?? ""
  const isSavingPrompt = promptSaveState.status === "pending"
  const configurationSaveStatus =
    configurationSaveState.status === "pending"
      ? "saving"
      : configurationSaveState.status === "success"
        ? "saved"
        : configurationSaveState.status
  const configurationSaveError = configurationSaveState.error?.message ?? ""
  const capabilities = capabilityState.data ?? null
  const capabilitiesLoading = capabilityState.status === "pending"
  const capabilitiesError = capabilityState.error?.message ?? ""
  const defaultModelConfiguration = useMemo(
    () =>
      createConfigurationFromCapabilities(
        capabilities,
        createDefaultModelConfiguration(),
      ),
    [capabilities],
  )
  const sourceUploadError = sourceUploadState.error?.message ?? ""
  const confirmationPending = confirmationState.status === "pending"
  const confirmationError = confirmationState.error?.message ?? ""

  useEffect(() => {
    if (!capabilities) return
    setConversationDraft((current) => {
      const defaultDraft = createDefaultConversationDraft()
      if (
        current.systemPrompt ||
        current.sourceIds.length > 0 ||
        current.temporary ||
        JSON.stringify(current.modelConfiguration) !==
          JSON.stringify(defaultDraft.modelConfiguration)
      ) {
        return current
      }
      return {
        ...current,
        modelConfiguration: defaultModelConfiguration,
      }
    })
  }, [capabilities, defaultModelConfiguration])

  const setInputValue = (value: string) => {
    setComposerDrafts((current) => ({ ...current, [composerKey]: value }))
  }
  const adjustConversationListTotal = (delta: number) => {
    setConversationListState((current) => ({
      ...current,
      data: {
        nextCursor: current.data?.nextCursor ?? null,
        total: Math.max(0, (current.data?.total ?? 0) + delta),
      },
    }))
  }

  const requestConfirmation = (request: ConfirmationRequest) => {
    setConfirmationState(idleAsyncState())
    setConfirmationRequest(request)
  }

  const runConfirmedAction = async () => {
    if (!confirmationRequest || confirmationPending) return
    setConfirmationState(pendingAsyncState())
    try {
      await confirmationRequest.onConfirm()
      setConfirmationState(successAsyncState(undefined))
      setConfirmationRequest(null)
    } catch (error) {
      setConfirmationState(errorAsyncState(normalizeError(error)))
    }
  }
  const scopedConfiguration: ConversationDraftConfiguration = activeConversation
    ? {
        systemPrompt: activeConversation.systemPrompt,
        modelConfiguration: activeConversation.modelConfiguration,
        sourceIds: activeConversation.sourceIds,
        temporary: activeConversation.temporary,
      }
    : conversationDraft
  const savedSystemPrompt = scopedConfiguration.systemPrompt
  const modelConfiguration = scopedConfiguration.modelConfiguration
  const selectedSources = new Set(scopedConfiguration.sourceIds)
  const tempChat = scopedConfiguration.temporary

  const updateScopedConfiguration = async (
    updater: (
      current: ConversationDraftConfiguration,
    ) => ConversationDraftConfiguration,
  ): Promise<void> => {
    const next = updater(scopedConfiguration)
    setConfigurationSaveState(pendingAsyncState(next))
    if (activeConversation) {
      const previous = scopedConfiguration
      const updatedAt = new Date().toISOString()
      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === activeConversation.id
            ? { ...conversation, ...next, updatedAt }
            : conversation,
        ),
      )
      try {
        await appServices.conversations.updateConfiguration(
          activeConversation.id,
          next,
        )
        setConfigurationSaveState(successAsyncState(next))
      } catch (error) {
        setConversations((current) =>
          current.map((conversation) =>
            conversation.id === activeConversation.id
              ? { ...conversation, ...previous }
              : conversation,
          ),
        )
        const normalized = normalizeError(error)
        setConfigurationSaveState(errorAsyncState(normalized, previous))
        throw normalized
      }
      return
    }

    setConversationDraft(next)
    setConfigurationSaveState(successAsyncState(next))
  }

  const updateModelConfiguration = <Key extends keyof ModelConfiguration,>(
    field: Key,
    value: ModelConfiguration[Key],
  ) => {
    void updateScopedConfiguration((current) => ({
      ...current,
      modelConfiguration: {
        ...current.modelConfiguration,
        [field]: value,
      },
    })).catch(reportBackgroundServiceError)
  }

  const setTemporaryChat = (temporary: boolean) => {
    void updateScopedConfiguration((current) => ({
      ...current,
      temporary,
    })).catch(reportBackgroundServiceError)
  }

  const setScopedSourceIds = (sourceIds: string[]) => {
    void updateScopedConfiguration((current) => ({
      ...current,
      sourceIds,
    })).catch(reportBackgroundServiceError)
  }

  const filteredSources = sourceDocuments.filter((source) =>
    source.filename.toLowerCase().includes(sourceSearch.toLowerCase()),
  )
  const summarySource = sourceDocuments.find(
    (source) => source.id === summarySourceId,
  )

  const closeSources = () => {
    setSourcesOpen(false)
    setSourceSearch("")
    setSummarySourceId(null)
  }

  const toggleSource = (sourceId: string) => {
    void updateScopedConfiguration((current) => {
      const next = new Set(current.sourceIds)
      if (next.has(sourceId)) next.delete(sourceId)
      else next.add(sourceId)
      return { ...current, sourceIds: [...next] }
    }).catch(reportBackgroundServiceError)
  }

  const selectAllVisibleSources = () => {
    void updateScopedConfiguration((current) => {
      const next = new Set(current.sourceIds)
      filteredSources.forEach((source) => next.add(source.id))
      return { ...current, sourceIds: [...next] }
    }).catch(reportBackgroundServiceError)
  }

  const deleteSource = async (sourceId: string) => {
    const source = sourceDocuments.find((document) => document.id === sourceId)
    if (!source) return

    await appServices.sources.delete(sourceId)
    setSourceDocuments((current) =>
      current.filter((document) => document.id !== sourceId),
    )
    const deletedAt = new Date().toISOString()
    setConversations((current) =>
      current.map((conversation) =>
        conversation.sourceIds.includes(sourceId)
          ? {
              ...conversation,
              sourceIds: conversation.sourceIds.filter((id) => id !== sourceId),
              updatedAt: deletedAt,
            }
          : conversation,
      ),
    )
    setConversationDraft((current) => ({
      ...current,
      sourceIds: current.sourceIds.filter((id) => id !== sourceId),
    }))
    if (summarySourceId === sourceId) setSummarySourceId(null)
  }

  const requestDeleteSource = (sourceId: string) => {
    const source = sourceDocuments.find((document) => document.id === sourceId)
    if (!source) return
    requestConfirmation({
      title: "Delete source?",
      description: `${source.filename} will be removed from Sources and every conversation that selected it.`,
      confirmLabel: "Delete source",
      tone: "danger",
      onConfirm: () => deleteSource(sourceId),
    })
  }

  const hasUnsavedPrompt = draftSystemPrompt !== savedSystemPrompt

  const showSourceSummary = async (sourceId: string) => {
    const summary = await appServices.sources.getSummary(sourceId)
    setSourceDocuments((current) =>
      current.map((source) =>
        source.id === sourceId ? { ...source, summary } : source,
      ),
    )
    setSummarySourceId(sourceId)
  }

  const openContextModal = () => {
    setDraftSystemPrompt(savedSystemPrompt)
    setModelFileError("")
    setActiveRight(null)
    setContextOpen(true)
  }

  const discardAndCloseContextModal = () => {
    setDraftSystemPrompt(savedSystemPrompt)
    if (hasUnsavedPrompt) setModelFileName(null)
    setModelFileError("")
    setContextOpen(false)
  }

  const closeContextModal = () => {
    if (!hasUnsavedPrompt) {
      discardAndCloseContextModal()
      return
    }
    requestConfirmation({
      title: "Discard unsaved changes?",
      description: "Your unsaved system prompt edits will be lost.",
      confirmLabel: "Discard changes",
      tone: "danger",
      onConfirm: discardAndCloseContextModal,
    })
  }

  const saveSystemPrompt = async () => {
    if (!hasUnsavedPrompt || isSavingPrompt) return

    setPromptSaveState(pendingAsyncState(draftSystemPrompt))
    try {
      await updateScopedConfiguration((current) => ({
        ...current,
        systemPrompt: draftSystemPrompt,
      }))
      setPromptSaveState(successAsyncState(draftSystemPrompt))
      setContextOpen(false)
    } catch (error) {
      const normalized = normalizeError(error)
      setPromptSaveState(errorAsyncState(normalized, savedSystemPrompt))
      setModelFileError(normalized.message)
    }
  }

  const clearSystemPrompt = () => {
    const clear = async () => {
      setPromptSaveState(pendingAsyncState(savedSystemPrompt))
      setDraftSystemPrompt("")
      try {
        await updateScopedConfiguration((current) => ({
          ...current,
          systemPrompt: "",
        }))
        setPromptSaveState(successAsyncState(""))
        setModelFileName(null)
        setModelFileError("")
      } catch (error) {
        const normalized = normalizeError(error)
        setDraftSystemPrompt(savedSystemPrompt)
        setPromptSaveState(errorAsyncState(normalized, savedSystemPrompt))
        setModelFileError(normalized.message)
        throw normalized
      }
    }
    if (!savedSystemPrompt) {
      void clear().catch(reportBackgroundServiceError)
      return
    }
    requestConfirmation({
      title: "Clear system prompt?",
      description: "The saved prompt for this conversation will be removed.",
      confirmLabel: "Clear prompt",
      tone: "danger",
      onConfirm: clear,
    })
  }

  const importModelFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    event.target.value = ""
    if (!file) return

    if (file.size > 1024 * 1024) {
      setModelFileError("Choose a text Modelfile smaller than 1 MB.")
      return
    }

    try {
      const content = new TextDecoder("utf-8", { fatal: true }).decode(
        await file.arrayBuffer(),
      )
      if (!content.trim()) {
        setModelFileError("That Modelfile is empty.")
        return
      }
      setDraftSystemPrompt(content)
      setModelFileName(file.name)
      setModelFileError("")
      systemPromptRef.current?.focus()
    } catch {
      setModelFileError(
        "Choose a valid UTF-8 text Modelfile smaller than 1 MB.",
      )
    }
  }

  const prepareAttachment = (attachmentId: string) => {
    const existingTimer = attachmentTimersRef.current.get(attachmentId)
    if (existingTimer) window.clearInterval(existingTimer)
    setAttachmentDrafts((current) => ({
      ...current,
      [composerKey]: (current[composerKey] ?? []).map((attachment) =>
        attachment.id === attachmentId
          ? {
              ...attachment,
              status: "uploading",
              progress: 10,
              error: undefined,
            }
          : attachment,
      ),
    }))
    const timer = window.setInterval(() => {
      let completed = false
      setAttachmentDrafts((current) => ({
        ...current,
        [composerKey]: (current[composerKey] ?? []).map((attachment) => {
          if (attachment.id !== attachmentId) return attachment
          const progress = Math.min(100, attachment.progress + 30)
          completed = progress >= 100
          const shouldFail =
            completed &&
            attachment.filename.toLowerCase().includes("fail") &&
            attachment.attempts === 0
          return {
            ...attachment,
            progress,
            attempts: shouldFail ? 1 : attachment.attempts,
            status: completed ? (shouldFail ? "failed" : "ready") : "uploading",
            error: shouldFail
              ? "Mock attachment preparation failed. Retry is available."
              : undefined,
          }
        }),
      }))
      if (completed) {
        window.clearInterval(timer)
        attachmentTimersRef.current.delete(attachmentId)
      }
    }, 120)
    attachmentTimersRef.current.set(attachmentId, timer)
  }

  const addComposerFiles = (files: File[]) => {
    const allowedTypes = new Set([
      "image/png",
      "image/jpeg",
      "image/webp",
      "application/pdf",
      "text/plain",
      "text/markdown",
      "text/csv",
    ])
    const currentAttachments = attachmentDrafts[composerKey] ?? []
    const next: ComposerAttachmentDraft[] = []
    const errors: string[] = []

    for (const file of files) {
      if (currentAttachments.length + next.length >= 5) {
        errors.push("You can attach up to five files per message.")
        break
      }
      if (file.size === 0) {
        errors.push(`${file.name} is empty.`)
        continue
      }
      if (file.size > 10 * 1024 * 1024) {
        errors.push(`${file.name} is larger than 10 MB.`)
        continue
      }
      if (!allowedTypes.has(file.type)) {
        errors.push(`${file.name} uses an unsupported file type.`)
        continue
      }
      const duplicate = [...currentAttachments, ...next].some(
        (attachment) =>
          attachment.filename.toLowerCase() === file.name.toLowerCase() &&
          attachment.size === file.size,
      )
      if (duplicate) {
        errors.push(`${file.name} is already attached.`)
        continue
      }

      const id = `attachment-${globalThis.crypto.randomUUID()}`
      const url = URL.createObjectURL(file)
      attachmentUrlsRef.current.add(url)
      next.push({
        id,
        filename: file.name,
        mediaType: file.type,
        size: file.size,
        status: "uploading",
        url,
        file,
        progress: 0,
        attempts: 0,
      })
    }

    if (next.length > 0) {
      setAttachmentDrafts((current) => ({
        ...current,
        [composerKey]: [...(current[composerKey] ?? []), ...next],
      }))
      next.forEach((attachment) => prepareAttachment(attachment.id))
    }
    setAttachmentErrors((current) => ({
      ...current,
      [composerKey]: errors.join(" "),
    }))
  }

  const removeComposerAttachment = (attachmentId: string) => {
    const attachment = composerAttachments.find(
      (item) => item.id === attachmentId,
    )
    if (attachment?.url) {
      URL.revokeObjectURL(attachment.url)
      attachmentUrlsRef.current.delete(attachment.url)
    }
    const timer = attachmentTimersRef.current.get(attachmentId)
    if (timer) window.clearInterval(timer)
    attachmentTimersRef.current.delete(attachmentId)
    setAttachmentDrafts((current) => ({
      ...current,
      [composerKey]: (current[composerKey] ?? []).filter(
        (item) => item.id !== attachmentId,
      ),
    }))
  }

  const uploadSources = async (files: File[]) => {
    setSourceUploadState(idleAsyncState())
    if (files.length > 10) {
      setSourceUploadState(
        errorAsyncState(
          validationError("Upload up to ten source documents at a time."),
        ),
      )
      return
    }
    const existingNames = new Set(
      sourceDocuments.map((source) => source.filename.toLowerCase()),
    )
    const allowedTypes = new Set([
      "application/pdf",
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      "text/plain",
      "text/markdown",
      "text/html",
      "text/csv",
      "text/tab-separated-values",
    ])
    const allowedExtensions = new Set([
      ".pdf",
      ".docx",
      ".txt",
      ".md",
      ".html",
      ".csv",
      ".tsv",
    ])
    const valid = files.filter((file) => {
      if (file.size === 0) {
        setSourceUploadState(
          errorAsyncState(validationError(`${file.name} is empty.`)),
        )
        return false
      }
      if (file.size > 25 * 1024 * 1024) {
        setSourceUploadState(
          errorAsyncState(
            validationError(`${file.name} is larger than 25 MB.`),
          ),
        )
        return false
      }
      const extension = file.name
        .slice(file.name.lastIndexOf("."))
        .toLowerCase()
      if (!allowedTypes.has(file.type) && !allowedExtensions.has(extension)) {
        setSourceUploadState(
          errorAsyncState(
            validationError(`${file.name} uses an unsupported file type.`),
          ),
        )
        return false
      }
      if (existingNames.has(file.name.toLowerCase())) {
        setSourceUploadState(
          errorAsyncState(
            validationError(`${file.name} already exists in Sources.`),
          ),
        )
        return false
      }
      existingNames.add(file.name.toLowerCase())
      return true
    })
    if (valid.length === 0) return

    setSourceUploadState(pendingAsyncState())
    setSourceUploadProgress(10)
    const progressTimer = window.setInterval(() => {
      setSourceUploadProgress((current) => Math.min(90, current + 15))
    }, 120)
    try {
      const uploaded = await appServices.sources.upload(valid)
      setSourceDocuments((current) => [...uploaded, ...current])
      setSourceUploadState(successAsyncState(uploaded))
      setSourceUploadProgress(100)
      window.setTimeout(() => setSourceUploadProgress(0), 700)
    } catch (error) {
      setSourceUploadState(errorAsyncState(normalizeError(error)))
      setSourceUploadProgress(0)
    } finally {
      window.clearInterval(progressTimer)
    }
  }

  const retrySource = async (sourceId: string) => {
    setSourceDocuments((current) =>
      current.map((source) =>
        source.id === sourceId
          ? { ...source, status: "processing", error: undefined }
          : source,
      ),
    )
    try {
      const retried = await appServices.sources.retry(sourceId)
      setSourceDocuments((current) =>
        current.map((source) => (source.id === sourceId ? retried : source)),
      )
    } catch (error) {
      setSourceDocuments((current) =>
        current.map((source) =>
          source.id === sourceId
            ? {
                ...source,
                status: "failed",
                error: normalizeError(error).message,
              }
            : source,
        ),
      )
    }
  }

  const handleLogout = async () => {
    try {
      await auth.signOut()
    } finally {
      setProfileMenuOpen(false)
      setConversations([])
      setSourceDocuments([])
      setActiveConversationId(null)
      navigate("/login", { replace: true })
    }
  }

  const selectConversation = (conversationId: string) => {
    setActiveConversationId(conversationId)
    setSearchOpen(false)
    setSearchValue("")
    setRecentsOpen(false)
    navigate(`/chat/${conversationId}`)
  }

  const startRenamingConversation = (conversation: Conversation) => {
    setRenameState(idleAsyncState())
    setEditingConversationId(conversation.id)
    setEditingConversationTitle(conversation.title)
  }

  const cancelRenamingConversation = () => {
    setEditingConversationId(null)
    setEditingConversationTitle("")
  }

  const saveConversationName = async (
    event: FormEvent<HTMLFormElement>,
    conversationId: string,
  ) => {
    event.preventDefault()
    const trimmedTitle = editingConversationTitle.trim()
    if (!trimmedTitle) return

    setRenameState(pendingAsyncState({ conversationId }))
    try {
      const renamed = await appServices.conversations.rename(
        conversationId,
        trimmedTitle,
      )
      setConversations((current) =>
        current.map((chat) =>
          chat.id === conversationId
            ? {
                ...chat,
                title: renamed.title,
                updatedAt: renamed.updatedAt,
              }
            : chat,
        ),
      )
      setRenameState(successAsyncState({ conversationId }))
      cancelRenamingConversation()
    } catch (error) {
      setRenameState(errorAsyncState(normalizeError(error), { conversationId }))
    }
  }

  const requestDeleteConversation = (conversationId: string) => {
    setRecentsOpen(false)
    if (!liveSettings.confirmBeforeDeleteChats) {
      void confirmDeleteConversation(conversationId).catch(
        reportBackgroundServiceError,
      )
      return
    }
    setDeleteConversationState(idleAsyncState({ conversationId }))
    setPendingDeleteConversationId(conversationId)
  }

  const confirmDeleteConversation = async (conversationIdOverride?: string) => {
    const conversationId = conversationIdOverride ?? pendingDeleteConversationId
    if (!conversationId) return

    const conversation = conversations.find(
      (chat) => chat.id === conversationId,
    )
    if (!conversation) {
      setPendingDeleteConversationId(null)
      return
    }

    const deletedIndex = conversations.findIndex(
      (item) => item.id === conversationId,
    )
    const remaining = conversations.filter((chat) => chat.id !== conversationId)
    const nextConversation =
      remaining[deletedIndex] ?? remaining[deletedIndex - 1] ?? null

    setDeleteConversationState(pendingAsyncState({ conversationId }))
    try {
      await appServices.conversations.delete(conversationId)
      setConversations(remaining)
      if (!conversation.temporary) {
        adjustConversationListTotal(-1)
      }
      if (editingConversationId === conversationId) cancelRenamingConversation()
      setRecentsOpen(false)
      setPendingDeleteConversationId(null)
      if (activeConversationId === conversationId) {
        setActiveConversationId(nextConversation?.id ?? null)
        navigate(nextConversation ? `/chat/${nextConversation.id}` : "/chat", {
          replace: true,
        })
      }
      setDeleteConversationState(successAsyncState({ conversationId }))
    } catch (error) {
      setDeleteConversationState(
        errorAsyncState(normalizeError(error), { conversationId }),
      )
    }
  }

  const sendMessage = async () => {
    const content = inputValue.trim()
    const readyAttachments = composerAttachments.filter(
      (attachment) => attachment.status === "ready",
    )
    if ((!content && readyAttachments.length === 0) || isSending) return

    const requestKey = composerKey
    setMessageSendState(pendingAsyncState({ key: requestKey }))
    let acceptedAssistantId: string | null = null
    let requestConversationId: string | null = activeConversation?.id ?? null
    try {
      let conversationId = requestConversationId

      if (!conversationId) {
        const conversation = await appServices.conversations.create({
          title: "New conversation",
          ...conversationDraft,
        })
        conversationId = conversation.id
        requestConversationId = conversation.id
        setConversations((current) => [
          conversation,
          ...current.filter((item) => item.id !== conversation.id),
        ])
        if (!conversation.temporary) {
          adjustConversationListTotal(1)
        }
        setActiveConversationId(conversationId)
        navigate(`/chat/${conversationId}`, { replace: true })
        setConversationDraft(createDefaultConversationDraft())
      }

      const messageAttachments = readyAttachments.map((attachment) => ({
        id: attachment.id,
        filename: attachment.filename,
        mediaType: attachment.mediaType,
        size: attachment.size,
        status: attachment.status,
        url: attachment.url,
        error: attachment.error,
      }))
      for await (const event of appServices.messages.stream({
        conversationId,
        content,
        attachmentIds: messageAttachments.map((attachment) => attachment.id),
        attachments: messageAttachments,
      })) {
        if (event.type === "accepted") {
          acceptedAssistantId = event.assistantMessage.id
          setMessageSendState(
            pendingAsyncState({
              key: requestKey,
              conversationId,
              assistantMessageId: event.assistantMessage.id,
            }),
          )
          setComposerDrafts((current) => ({ ...current, [requestKey]: "" }))
          setAttachmentDrafts((current) => ({ ...current, [requestKey]: [] }))
          setConversations((current) =>
            current.map((conversation) =>
              conversation.id === conversationId
                ? {
                    ...conversation,
                    messages: [
                      ...conversation.messages,
                      event.userMessage,
                      event.assistantMessage,
                    ],
                  }
                : conversation,
            ),
          )
        } else if (event.type === "delta") {
          setConversations((current) =>
            updateConversationMessage(
              current,
              conversationId,
              event.messageId,
              (message) => ({
                ...message,
                status: "streaming",
                content: `${message.content}${event.delta}`,
              }),
            ),
          )
        } else {
          setConversations((current) =>
            updateConversationMessage(
              current,
              conversationId,
              event.message.id,
              () => event.message,
            ),
          )
        }
      }
      const updatedConversation =
        await appServices.conversations.get(conversationId)

      setConversations((current) =>
        current.map((conversation) =>
          conversation.id === conversationId
            ? updatedConversation
            : conversation,
        ),
      )
      setMessageSendState(
        successAsyncState({
          key: requestKey,
          conversationId,
          assistantMessageId: acceptedAssistantId ?? undefined,
        }),
      )
    } catch (error) {
      const normalized = normalizeError(error)
      setMessageSendState(
        errorAsyncState(normalized, {
          key: requestKey,
          conversationId: requestConversationId ?? undefined,
          assistantMessageId: acceptedAssistantId ?? undefined,
        }),
      )
      if (acceptedAssistantId && requestConversationId) {
        const failedMessageId = acceptedAssistantId
        const failedConversationId = requestConversationId
        setConversations((current) =>
          updateConversationMessage(
            current,
            failedConversationId,
            failedMessageId,
            (message) => ({
              ...message,
              status: "failed",
              error: normalized.message,
            }),
          ),
        )
      }
    }
  }

  const cancelMessage = async (messageId: string) => {
    if (!activeConversationId) return
    await appServices.messages.cancel(activeConversationId, messageId)
    setConversations((current) =>
      updateConversationMessage(
        current,
        activeConversationId,
        messageId,
        (message) => ({
          ...message,
          status: "stopped",
          error: "Response stopped by the user.",
        }),
      ),
    )
  }

  const retryMessage = async (messageId: string) => {
    if (!activeConversationId) return
    setConversations((current) =>
      updateConversationMessage(
        current,
        activeConversationId,
        messageId,
        (message) => ({ ...message, status: "pending", error: undefined }),
      ),
    )
    try {
      const retried = await appServices.messages.retry(
        activeConversationId,
        messageId,
      )
      setConversations((current) =>
        updateConversationMessage(
          current,
          activeConversationId,
          messageId,
          () => retried,
        ),
      )
    } catch (error) {
      setConversations((current) =>
        updateConversationMessage(
          current,
          activeConversationId,
          messageId,
          (message) => ({
            ...message,
            status: "failed",
            error: normalizeError(error).message,
          }),
        ),
      )
    }
  }

  const startNewConversation = async () => {
    const conversation = await appServices.conversations.create({
      title: "New conversation",
      systemPrompt: "",
      modelConfiguration: defaultModelConfiguration,
      sourceIds: [],
      temporary: false,
    })
    setConversations((current) => [conversation, ...current])
    adjustConversationListTotal(1)
    setActiveConversationId(conversation.id)
    navigate(`/chat/${conversation.id}`)
    setSearchValue("")
    setDraftSystemPrompt("")
    setModelFileName(null)
    setModelFileError("")
    setSummarySourceId(null)
    setActiveRight(null)
    setContextOpen(false)
    setSourcesOpen(false)
    setRecentsOpen(false)
    setNewChatNoticeOpen(true)

    if (newChatNoticeTimerRef.current !== null) {
      window.clearTimeout(newChatNoticeTimerRef.current)
    }
    newChatNoticeTimerRef.current = window.setTimeout(() => {
      setNewChatNoticeOpen(false)
      newChatNoticeTimerRef.current = null
    }, 3500)
  }

  const loadMoreConversations = async () => {
    if (!conversationNextCursor || conversationListLoading) return
    setConversationListState(
      pendingAsyncState({
        nextCursor: conversationNextCursor,
        total: conversationListTotal,
      }),
    )
    try {
      const page = await appServices.conversations.list({
        cursor: conversationNextCursor,
        limit: 20,
      })
      const loaded = await Promise.all(
        page.items.map((summary) => appServices.conversations.get(summary.id)),
      )
      setConversations((current) => {
        const existingIds = new Set(
          current.map((conversation) => conversation.id),
        )
        return [
          ...current,
          ...loaded.filter((conversation) => !existingIds.has(conversation.id)),
        ]
      })
      setConversationListState(
        successAsyncState({ nextCursor: page.nextCursor, total: page.total }),
      )
    } catch (error) {
      setConversationListState(
        errorAsyncState(normalizeError(error), {
          nextCursor: conversationNextCursor,
          total: conversationListTotal,
        }),
      )
    }
  }

  const retryConversationList = async () => {
    setConversationListState(
      pendingAsyncState({ nextCursor: null, total: conversationListTotal }),
    )
    try {
      const page = await appServices.conversations.list({ limit: 20 })
      const loaded = await Promise.all(
        page.items.map((summary) => appServices.conversations.get(summary.id)),
      )
      setConversations(loaded)
      setConversationListState(
        successAsyncState({ nextCursor: page.nextCursor, total: page.total }),
      )
    } catch (error) {
      setConversationListState(
        errorAsyncState(normalizeError(error), {
          nextCursor: null,
          total: conversationListTotal,
        }),
      )
    }
  }

  useEffect(() => {
    let cancelled = false
    const loadServiceState = async () => {
      try {
        const page = await appServices.conversations.list({ limit: 20 })
        const sources = await appServices.sources.list().catch(() => [])
        const loadedConversations = await Promise.all(
          page.items.map((summary) =>
            appServices.conversations.get(summary.id),
          ),
        )
        if (cancelled) return
        setConversations((current) =>
          current.length > 0 ? current : loadedConversations,
        )
        setSourceDocuments((current) =>
          current.length > 0 ? current : sources,
        )
        setConversationListState(
          successAsyncState({ nextCursor: page.nextCursor, total: page.total }),
        )
        setServiceStateLoaded(true)
      } catch (error) {
        if (!cancelled) {
          setConversationListState(
            errorAsyncState(normalizeError(error), {
              nextCursor: null,
              total: 0,
            }),
          )
          setServiceStateLoaded(true)
        }
      }
    }

    void loadServiceState()
    return () => {
      cancelled = true
    }
  }, [auth.session?.user.id])

  useEffect(() => {
    let cancelled = false

    const loadSidebarProfile = async () => {
      try {
        const profile = await appServices.profile.load()
        if (cancelled) return

        setSidebarProfileName(
          profile.profile.displayName.trim() ||
            auth.session?.user.displayName ||
            "User",
        )
        setSidebarProfileId(
          profile.profile.id || auth.session?.user.id || "user-local",
        )
        setSidebarProfileAvatarUrl(profile.profile.avatarUrl)
      } catch {
        if (!cancelled) {
          setSidebarProfileName(auth.session?.user.displayName || "User")
          setSidebarProfileId(auth.session?.user.id || "user-local")
          setSidebarProfileAvatarUrl(null)
        }
      }
    }

    void loadSidebarProfile()
    return () => {
      cancelled = true
    }
  }, [location.pathname, auth.session?.user.displayName, auth.session?.user.id])

  useEffect(() => {
    if (!serviceStateLoaded) return
    if (!routeConversationId) {
      setActiveConversationId(null)
      return
    }

    const routeConversationExists = conversations.some(
      (conversation) => conversation.id === routeConversationId,
    )
    if (routeConversationExists) {
      setActiveConversationId(routeConversationId)
      return
    }

    let cancelled = false
    void appServices.conversations
      .get(routeConversationId)
      .then((conversation) => {
        if (cancelled) return
        setConversations((current) => [conversation, ...current])
        setActiveConversationId(conversation.id)
      })
      .catch(() => {
        if (!cancelled) navigate("/chat", { replace: true })
      })
    return () => {
      cancelled = true
    }
  }, [conversations, navigate, routeConversationId, serviceStateLoaded])

  useEffect(() => {
    const attachmentTimers = attachmentTimersRef.current
    const attachmentUrls = attachmentUrlsRef.current
    return () => {
      if (newChatNoticeTimerRef.current !== null) {
        window.clearTimeout(newChatNoticeTimerRef.current)
      }
      attachmentTimers.forEach((timer) => window.clearInterval(timer))
      attachmentUrls.forEach((url) => URL.revokeObjectURL(url))
      attachmentUrls.clear()
    }
  }, [])

  const handlePointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect()
    setCursor({ x: event.clientX - rect.left, y: event.clientY - rect.top })
  }

  const mask = `radial-gradient(circle at ${cursor.x}px ${cursor.y}px, #000 72px, transparent 120px)`

  const container: CSSProperties = {
    position: "relative",
    width: "100%",
    minHeight: "100vh",
    overflow: "hidden",
    backgroundColor: "var(--app-bg)",
    fontFamily: "'Inter', system-ui, sans-serif",
  }
  const dots: CSSProperties = {
    position: "absolute",
    inset: 0,
    backgroundImage:
      "radial-gradient(circle at center, var(--app-dots-soft) 1.2px, transparent 1.4px)",
    backgroundSize: "18px 18px",
    pointerEvents: "none",
  }
  const dotsHover: CSSProperties = {
    position: "absolute",
    inset: 0,
    backgroundImage:
      "radial-gradient(circle at center, var(--app-dots-strong) 2.1px, transparent 2.4px)",
    backgroundSize: "18px 18px",
    opacity: hovering ? 1 : 0,
    maskImage: mask,
    WebkitMaskImage: mask,
    transition: "opacity 0.15s",
    pointerEvents: "none",
  }

  const pendingDeleteConversation = conversations.find(
    (conversation) => conversation.id === pendingDeleteConversationId,
  )
  const filteredChats = conversations.filter(
    (c) =>
      !c.temporary && c.title.toLowerCase().includes(searchValue.toLowerCase()),
  )

  return (
    <div
      style={container}
      onPointerEnter={() => setHovering(true)}
      onPointerMove={handlePointerMove}
      onPointerLeave={() => setHovering(false)}
      onClick={(event) => {
        if (!sidebarOpen) return
        const target = event.target as Node
        const sidebarElement = document.getElementById(
          "conversation-sidebar-content",
        )
        if (sidebarElement && !sidebarElement.contains(target)) {
          setSidebarOpen(false)
        }
      }}
    >
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault()
          const mainContent = document.getElementById("main-content")
          mainContent?.focus({ preventScroll: true })
          mainContent?.scrollIntoView({ block: "start" })
        }}
      >
        Skip to main content
      </a>
      <div style={dots} />
      <div style={dotsHover} />

      {sidebarOpen && (
        <button
          type="button"
          className="mobile-sidebar-backdrop"
          aria-label="Close conversation navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {newChatNoticeOpen && (
        <div className="new-chat-notice" role="status" aria-live="polite">
          <span className="new-chat-notice-icon" aria-hidden="true">
            ✓
          </span>
          <span>
            <strong>New conversation started</strong>
            <small>You’re ready to begin with a clean chat.</small>
          </span>
          <button
            type="button"
            onClick={() => setNewChatNoticeOpen(false)}
            aria-label="Dismiss new conversation message"
          >
            ×
          </button>
        </div>
      )}

      <ConversationSidebar
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
        startNewConversation={() => {
          void startNewConversation().catch(reportBackgroundServiceError)
        }}
        searchButtonRef={searchButtonRef}
        recentsButtonRef={recentsButtonRef}
        profileButtonRef={profileButtonRef}
        setSearchOpen={setSearchOpen}
        setSearchValue={setSearchValue}
        setRecentsOpen={setRecentsOpen}
        setProfileMenuOpen={setProfileMenuOpen}
        recentsOpen={recentsOpen}
        searchValue={searchValue}
        filteredChats={filteredChats}
        listLoading={conversationListLoading}
        listError={conversationListError}
        listTotal={conversationListTotal}
        hasMoreConversations={Boolean(conversationNextCursor)}
        onLoadMoreConversations={() => void loadMoreConversations()}
        onRetryConversationList={() => void retryConversationList()}
        activeConversationId={activeConversationId}
        selectConversation={selectConversation}
        editingConversationId={editingConversationId}
        saveConversationName={(event, conversationId) => {
          void saveConversationName(event, conversationId).catch(
            reportBackgroundServiceError,
          )
        }}
        editingConversationTitle={editingConversationTitle}
        renamingConversationId={renamingConversationId}
        conversationActionError={conversationActionError}
        setEditingConversationTitle={setEditingConversationTitle}
        cancelRenamingConversation={cancelRenamingConversation}
        startRenamingConversation={startRenamingConversation}
        requestDeleteConversation={requestDeleteConversation}
        profileMenuOpen={profileMenuOpen}
        profileDisplayName={sidebarProfileName}
        profileId={sidebarProfileId}
        profileAvatarUrl={sidebarProfileAvatarUrl}
      />
      <ProfileMenu
        profileMenuOpen={profileMenuOpen}
        setProfileMenuOpen={setProfileMenuOpen}
        sidebarOpen={sidebarOpen}
        onNavigate={(path) => navigate(path)}
        handleLogout={() => {
          void handleLogout().catch(reportBackgroundServiceError)
        }}
        profileButtonRef={profileButtonRef}
      />

      <RightConfigurationToolbar
        tempChat={tempChat}
        onTemporaryChange={setTemporaryChat}
        activeRight={activeRight}
        setActiveRight={setActiveRight}
        chatConfigButtonRef={chatConfigButtonRef}
        contextButtonRef={contextButtonRef}
        contextOpen={contextOpen}
        savedSystemPrompt={savedSystemPrompt}
        openContextModal={openContextModal}
        sourcesButtonRef={sourcesButtonRef}
        sourcesOpen={sourcesOpen}
        selectedSources={selectedSources}
        setSourcesOpen={setSourcesOpen}
      />

      {/* ── Chat configuration modal ── */}
      <ChatConfigurationModal
        open={activeRight === "model"}
        onClose={() => setActiveRight(null)}
        llmModelSelectRef={llmModelSelectRef}
        returnFocusRef={chatConfigButtonRef}
        configuration={modelConfiguration}
        capabilities={capabilities}
        capabilitiesLoading={capabilitiesLoading}
        capabilitiesError={capabilitiesError}
        onConfigurationChange={updateModelConfiguration}
        saveStatus={configurationSaveStatus}
        saveError={configurationSaveError}
      />

      {/* ── Center empty state ── */}
      <DeleteConversationModal
        conversation={pendingDeleteConversation}
        cancelButtonRef={deleteCancelButtonRef}
        returnFocusRef={composerInputRef}
        pending={isDeletingConversation}
        error={deleteConversationError}
        onCancel={() => {
          setPendingDeleteConversationId(null)
          setDeleteConversationState(idleAsyncState())
        }}
        onConfirm={() => {
          void confirmDeleteConversation().catch(reportBackgroundServiceError)
        }}
      />

      <ChatTranscript
        activeConversation={activeConversation}
        tempChat={tempChat}
        showMessageTimestamps={liveSettings.showMessageTimestamps}
        onCancelMessage={(messageId) => {
          void cancelMessage(messageId).catch(reportBackgroundServiceError)
        }}
        onRetryMessage={(messageId) => void retryMessage(messageId)}
        onRegenerateMessage={(messageId) => void retryMessage(messageId)}
      />

      {/* ── Search modal ── */}
      <SearchChatsModal
        open={searchOpen}
        searchValue={searchValue}
        setSearchValue={setSearchValue}
        setSearchOpen={setSearchOpen}
        conversations={conversations.filter(
          (conversation) => !conversation.temporary,
        )}
        selectConversation={selectConversation}
        searchInputRef={searchInputRef}
        searchButtonRef={searchButtonRef}
      />

      {/* ── Context / System Prompt modal ── */}
      <SystemPromptModal
        open={contextOpen}
        contextButtonRef={contextButtonRef}
        systemPromptRef={systemPromptRef}
        closeContextModal={closeContextModal}
        draftSystemPrompt={draftSystemPrompt}
        setDraftSystemPrompt={setDraftSystemPrompt}
        modelFileRef={modelFileRef}
        importModelFile={importModelFile}
        modelFileName={modelFileName}
        setModelFileName={setModelFileName}
        modelFileError={modelFileError}
        setModelFileError={setModelFileError}
        savedSystemPrompt={savedSystemPrompt}
        hasUnsavedPrompt={hasUnsavedPrompt}
        isSavingPrompt={isSavingPrompt}
        clearSystemPrompt={clearSystemPrompt}
        saveSystemPrompt={saveSystemPrompt}
      />

      {/* ── Sources modal ── */}
      {sourcesOpen && (
        <SourcesModal
          searchValue={sourceSearch}
          onSearchChange={setSourceSearch}
          sources={filteredSources}
          allSourcesCount={sourceDocuments.length}
          selectedSources={selectedSources}
          summarySource={summarySource}
          onToggleSource={toggleSource}
          onSelectAll={selectAllVisibleSources}
          onClearSelection={() => setScopedSourceIds([])}
          onShowSummary={(sourceId) => {
            void showSourceSummary(sourceId).catch(reportBackgroundServiceError)
          }}
          onDeleteSource={requestDeleteSource}
          onRetrySource={(sourceId) => void retrySource(sourceId)}
          onUploadSources={(files) => void uploadSources(files)}
          uploadProgress={sourceUploadProgress}
          uploadError={sourceUploadError}
          onCloseSummary={() => setSummarySourceId(null)}
          onClose={closeSources}
          initialFocusRef={sourcesSearchRef}
          returnFocusRef={sourcesButtonRef}
        />
      )}

      {/* ── Recents popover ── */}
      <RecentChatsPopover
        recentsOpen={recentsOpen}
        setRecentsOpen={setRecentsOpen}
        conversations={conversations.filter(
          (conversation) => !conversation.temporary,
        )}
        activeConversationId={activeConversationId}
        selectConversation={selectConversation}
        editingConversationId={editingConversationId}
        saveConversationName={(event, conversationId) => {
          void saveConversationName(event, conversationId).catch(
            reportBackgroundServiceError,
          )
        }}
        editingConversationTitle={editingConversationTitle}
        renamingConversationId={renamingConversationId}
        conversationActionError={conversationActionError}
        setEditingConversationTitle={setEditingConversationTitle}
        cancelRenamingConversation={cancelRenamingConversation}
        startRenamingConversation={startRenamingConversation}
        requestDeleteConversation={requestDeleteConversation}
        recentsButtonRef={recentsButtonRef}
      />

      {/* Composer */}
      <ChatComposer
        inputValue={inputValue}
        onInputChange={setInputValue}
        onSend={() => {
          void sendMessage()
        }}
        isSending={isSending}
        attachments={composerAttachments}
        attachmentError={attachmentError || messageError}
        onFilesSelected={addComposerFiles}
        onRemoveAttachment={removeComposerAttachment}
        onRetryAttachment={prepareAttachment}
        fileInputRef={fileRef}
        inputRef={composerInputRef}
        sendOnEnter={liveSettings.sendOnEnter}
        onComposerClick={() => {
          if (sidebarOpen) {
            setSidebarOpen(false)
          }
        }}
      />

      <ConfirmationModal
        request={confirmationRequest}
        pending={confirmationPending}
        error={confirmationError}
        cancelButtonRef={confirmationCancelRef}
        onCancel={() => {
          if (confirmationPending) return
          setConfirmationRequest(null)
          setConfirmationState(idleAsyncState())
        }}
        onConfirm={() => void runConfirmedAction()}
      />
    </div>
  )
}

function reportBackgroundServiceError(error: unknown) {
  console.error(normalizeError(error))
}

function updateConversationMessage(
  conversations: Conversation[],
  conversationId: string,
  messageId: string,
  updater: (message: ChatMessage) => ChatMessage,
): Conversation[] {
  return conversations.map((conversation) =>
    conversation.id === conversationId
      ? {
          ...conversation,
          messages: conversation.messages.map((message) =>
            message.id === messageId ? updater(message) : message,
          ),
        }
      : conversation,
  )
}
