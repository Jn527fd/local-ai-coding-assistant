export const MAX_CHATS = 5;
export const CHAT_STORAGE_PREFIX = "local-ai-coding-assistant.chats";

export function createChat() {
  return {
    id:
      typeof globalThis.crypto?.randomUUID === "function"
        ? globalThis.crypto.randomUUID()
        : `${Date.now()}-${Math.random()}`,
    title: "Untitled thread",
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}

export function chatStorageKey(username) {
  return `${CHAT_STORAGE_PREFIX}.${username}`;
}

export function loadChats(username) {
  try {
    const parsed = JSON.parse(
      window.localStorage.getItem(chatStorageKey(username)) || "[]",
    );
    if (!Array.isArray(parsed)) {
      return [createChat()];
    }

    const validChats = parsed
      .filter(
        (chat) =>
          chat &&
          typeof chat.id === "string" &&
          typeof chat.title === "string" &&
          Array.isArray(chat.messages),
      )
      .map((chat) => ({
        ...chat,
        messages: chat.messages.filter(
          (message) =>
            message &&
            (message.role === "user" || message.role === "assistant") &&
            typeof message.content === "string" &&
            message.content.length > 0,
        ),
      }))
      .slice(0, MAX_CHATS);

    return validChats.length > 0 ? validChats : [createChat()];
  } catch {
    return [createChat()];
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
