export const MAX_CHATS = 5;
export const CHAT_STORAGE_PREFIX = "local-ai-coding-assistant.chats";
export const CONVERSATION_PERSISTENCE_PREFIX =
  "local-ai-coding-assistant.conversation-persistence";
export const PERSISTENCE_MODE_LOCAL = "local";
export const PERSISTENCE_MODE_BACKEND = "backend";

export const CONVERSATION_SETTING_KEYS = [
  "llmModel",
  "embedderModel",
  "ocrEngine",
  "pdfParser",
  "chunker",
  "vectorDatabase",
  "ragPipeline",
  "reranker",
  "contextCompressor",
  "visionModel",
];

export const BASE_CONVERSATION_SETTINGS = Object.freeze({
  llmModel: "",
  embedderModel: "",
  ocrEngine: "none",
  pdfParser: "none",
  chunker: "recursive",
  vectorDatabase: "chroma",
  ragPipeline: "basic",
  reranker: "none",
  contextCompressor: "none",
  visionModel: "none",
});

function cloneSettings(settings) {
  return { ...settings };
}

function capabilityId(item) {
  if (!item || typeof item !== "object") {
    return "";
  }
  return typeof item.id === "string"
    ? item.id
    : typeof item.name === "string"
      ? item.name
      : "";
}

function availableCapabilityIds(capabilities, key) {
  const items = capabilities?.[key];
  if (!Array.isArray(items)) {
    return [];
  }

  return items
    .filter((item) => item?.available !== false)
    .map(capabilityId)
    .filter(Boolean);
}

function preferredCapability(ids, preferredId) {
  return (
    ids.find(
      (id) => id === preferredId || id.startsWith(`${preferredId}:`),
    ) || ""
  );
}

function firstAvailable(ids) {
  return [...ids].sort((left, right) => left.localeCompare(right))[0] || "";
}

export function buildDefaultConversationSettings({
  capabilities = null,
} = {}) {
  const llmModels = availableCapabilityIds(capabilities, "llmModels");
  const embedderModels = availableCapabilityIds(capabilities, "embedderModels");
  const pdfParsers = availableCapabilityIds(capabilities, "pdfParsers");

  return {
    ...BASE_CONVERSATION_SETTINGS,
    llmModel: firstAvailable(llmModels),
    embedderModel:
      preferredCapability(embedderModels, "nomic-embed-text") ||
      firstAvailable(embedderModels),
    pdfParser:
      pdfParsers.includes("pymupdf")
        ? "pymupdf"
        : pdfParsers.includes("pdfplumber")
          ? "pdfplumber"
          : pdfParsers.includes("docling")
            ? "docling"
            : "none",
  };
}

export function normalizeConversationSettings(settings, defaults = {}) {
  const source = settings && typeof settings === "object" ? settings : {};
  const fallback = {
    ...BASE_CONVERSATION_SETTINGS,
    ...defaults,
  };

  return CONVERSATION_SETTING_KEYS.reduce((normalized, key) => {
    const value = source[key];
    normalized[key] =
      typeof value === "string" && value.trim() ? value : fallback[key];
    return normalized;
  }, {});
}

export function normalizeChat(chat, defaultSettings = BASE_CONVERSATION_SETTINGS) {
  const normalizedSettings = normalizeConversationSettings(
    chat?.settings,
    defaultSettings,
  );

  return {
    ...chat,
    messages: chat.messages.filter(
      (message) =>
        message &&
        (message.role === "user" || message.role === "assistant") &&
        typeof message.content === "string" &&
        message.content.length > 0,
    ),
    settings: normalizedSettings,
  };
}

export function normalizeChats(chats, defaultSettings = BASE_CONVERSATION_SETTINGS) {
  if (!Array.isArray(chats)) {
    return [createChat(defaultSettings)];
  }

  const validChats = chats
    .filter(
      (chat) =>
        chat &&
        typeof chat.id === "string" &&
        typeof chat.title === "string" &&
        Array.isArray(chat.messages),
    )
    .map((chat) => normalizeChat(chat, defaultSettings))
    .slice(0, MAX_CHATS);

  return validChats.length > 0 ? validChats : [createChat(defaultSettings)];
}

export function createChat(defaultSettings = BASE_CONVERSATION_SETTINGS) {
  return {
    id:
      typeof globalThis.crypto?.randomUUID === "function"
        ? globalThis.crypto.randomUUID()
        : `${Date.now()}-${Math.random()}`,
    title: "Untitled thread",
    messages: [],
    updatedAt: new Date().toISOString(),
    settings: cloneSettings(defaultSettings),
  };
}

export function chatStorageKey(username) {
  return `${CHAT_STORAGE_PREFIX}.${username}`;
}

export function conversationPersistenceKey(username) {
  return `${CONVERSATION_PERSISTENCE_PREFIX}.${username}`;
}

export function loadConversationPersistenceMode(username) {
  try {
    const value = window.localStorage.getItem(conversationPersistenceKey(username));
    return value === PERSISTENCE_MODE_BACKEND
      ? PERSISTENCE_MODE_BACKEND
      : PERSISTENCE_MODE_LOCAL;
  } catch {
    return PERSISTENCE_MODE_LOCAL;
  }
}

export function saveConversationPersistenceMode(username, mode) {
  const normalizedMode =
    mode === PERSISTENCE_MODE_BACKEND
      ? PERSISTENCE_MODE_BACKEND
      : PERSISTENCE_MODE_LOCAL;
  window.localStorage.setItem(
    conversationPersistenceKey(username),
    normalizedMode,
  );
  return normalizedMode;
}

export function loadChats(username, defaultSettings = BASE_CONVERSATION_SETTINGS) {
  try {
    const parsed = JSON.parse(
      window.localStorage.getItem(chatStorageKey(username)) || "[]",
    );
    return normalizeChats(parsed, defaultSettings);
  } catch {
    return [createChat(defaultSettings)];
  }
}

export function titleFromMessage(message) {
  const singleLine = message.replace(/\s+/g, " ").trim();
  return singleLine.length > 44
    ? `${singleLine.slice(0, 44)}...`
    : singleLine;
}

export function formatRelativeTime(value) {
  if (!value) {
    return "Just now";
  }

  const timestamp = new Date(value).getTime();
  if (Number.isNaN(timestamp)) {
    return "Recently";
  }

  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));
  if (elapsedSeconds < 60) {
    return "Just now";
  }

  const elapsedMinutes = Math.floor(elapsedSeconds / 60);
  if (elapsedMinutes < 60) {
    return `${elapsedMinutes}m ago`;
  }

  const elapsedHours = Math.floor(elapsedMinutes / 60);
  if (elapsedHours < 24) {
    return `${elapsedHours}h ago`;
  }

  const elapsedDays = Math.floor(elapsedHours / 24);
  return `${elapsedDays}d ago`;
}
