import { resolveApiBaseUrl } from "./apiBase.js";

const configuredApiBaseUrl = import.meta.env?.VITE_API_BASE_URL || "";

export const API_BASE_URL = resolveApiBaseUrl(
  configuredApiBaseUrl,
  globalThis.location,
);

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function readCookie(name) {
  if (typeof document === "undefined" || !document.cookie) {
    return "";
  }
  return document.cookie
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${name}=`))
    ?.slice(name.length + 1) || "";
}

function errorMessageFromDetail(detail, status) {
  if (typeof detail === "string" && detail) {
    return detail;
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (!item || typeof item !== "object" || typeof item.msg !== "string") {
          return "";
        }

        const location = Array.isArray(item.loc)
          ? item.loc.filter((part) => part !== "body").join(".")
          : "";
        return location ? `${location}: ${item.msg}` : item.msg;
      })
      .filter(Boolean);

    if (messages.length > 0) {
      return messages.join(" ");
    }
  }

  return `Request failed with status ${status}.`;
}

async function request(
  path,
  { method = "GET", apiKey = "", body, formData } = {},
) {
  const headers = {};

  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  if (!["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) {
    const csrfToken = readCookie("local_ai_csrf");
    if (csrfToken) {
      headers["X-CSRF-Token"] = decodeURIComponent(csrfToken);
    }
  }

  if (body !== undefined && formData === undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      credentials: "include",
      body:
        formData !== undefined
          ? formData
          : body === undefined
            ? undefined
            : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(
      `Could not reach the backend at ${API_BASE_URL}. Is FastAPI running?`,
    );
  }

  const responseText = await response.text();
  let data = null;

  if (responseText) {
    try {
      data = JSON.parse(responseText);
    } catch {
      data = responseText;
    }
  }

  if (!response.ok) {
    const detail =
      data && typeof data === "object" && "detail" in data
        ? data.detail
        : data;
    throw new ApiError(
      errorMessageFromDetail(detail, response.status),
      response.status,
    );
  }

  return data;
}

export function checkHealth() {
  return request("/health");
}

export async function login(username, password) {
  await request("/auth/login", {
    method: "POST",
    body: { username, password },
  });

  try {
    return await getCurrentUser();
  } catch (error) {
    throw new ApiError(
      "Login succeeded, but the browser session cookie could not be verified. Open the frontend and backend through the same host or IP address, then try again.",
      error.status,
    );
  }
}

export function getCurrentUser() {
  return request("/auth/me");
}

export function logout() {
  return request("/auth/logout", { method: "POST" });
}

export function getAccountStatus(apiKey) {
  return request("/account/status", { apiKey });
}

export function updateApiKey(apiKey) {
  return request("/account/api-key", {
    method: "PUT",
    body: { api_key: apiKey },
  });
}

export function getModelStatus() {
  return request("/models/status");
}

export function getDiagnosticsStatus(apiKey) {
  return request("/diagnostics/status", { apiKey });
}

export function getSupportBundle(apiKey) {
  return request("/diagnostics/support-bundle", { apiKey });
}

function buildChatRequestBody(
  message,
  history = [],
  conversationSettings = null,
  conversationId = "",
  ragOptions = null,
  images = [],
) {
  const body = { message, history };
  if (conversationId) {
    body.conversationId = conversationId;
  }
  if (conversationSettings) {
    body.conversationSettings = conversationSettings;
  }
  if (ragOptions) {
    body.ragOptions = ragOptions;
    if (Array.isArray(ragOptions.documentIds) && ragOptions.documentIds.length > 0) {
      body.attachmentDocumentIds = ragOptions.documentIds;
    }
  }
  if (images.length > 0) {
    body.images = images;
  }
  return body;
}

export function getComponentCapabilities() {
  return request("/components/capabilities");
}

export function listConversations() {
  return request("/conversations");
}

export function saveConversation(conversation) {
  return request(`/conversations/${encodeURIComponent(conversation.id)}`, {
    method: "PUT",
    body: conversation,
  });
}

export function deleteConversation(conversationId) {
  return request(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
}

export function importConversations(conversations, { replace = false } = {}) {
  return request("/conversations/import", {
    method: "POST",
    body: {
      conversations,
      replace,
    },
  });
}

export function exportConversations() {
  return request("/conversations/export/all");
}

export function switchModel(model) {
  return request("/models/switch", {
    method: "POST",
    body: { model },
  });
}

export function sendChat(
  apiKey,
  message,
  history = [],
  conversationSettings = null,
  conversationId = "",
  ragOptions = null,
  images = [],
) {
  const body = buildChatRequestBody(
    message,
    history,
    conversationSettings,
    conversationId,
    ragOptions,
    images,
  );

  return request("/chat", {
    method: "POST",
    apiKey,
    body,
  });
}

function parseSseFrames(buffer) {
  const frames = buffer.split(/\n\n/);
  return {
    completeFrames: frames.slice(0, -1),
    remainder: frames.at(-1) || "",
  };
}

function parseSseFrame(frame) {
  let event = "message";
  const dataLines = [];
  frame.split(/\n/).forEach((line) => {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  });
  if (dataLines.length === 0) {
    return { event, data: null };
  }
  const dataText = dataLines.join("\n");
  try {
    return { event, data: JSON.parse(dataText) };
  } catch {
    return { event, data: dataText };
  }
}

export async function sendChatStream(
  apiKey,
  message,
  history = [],
  conversationSettings = null,
  conversationId = "",
  ragOptions = null,
  images = [],
  callbacks = {},
) {
  const headers = {
    "Content-Type": "application/json",
  };
  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}/chat/stream`, {
      method: "POST",
      headers,
      credentials: "include",
      body: JSON.stringify(
        buildChatRequestBody(
          message,
          history,
          conversationSettings,
          conversationId,
          ragOptions,
          images,
        ),
      ),
    });
  } catch {
    throw new ApiError(
      `Could not reach the backend at ${API_BASE_URL}. Is FastAPI running?`,
    );
  }

  if (!response.ok) {
    const responseText = await response.text();
    let data = responseText;
    try {
      data = responseText ? JSON.parse(responseText) : null;
    } catch {
      // Keep the raw response text.
    }
    const detail =
      data && typeof data === "object" && "detail" in data
        ? data.detail
        : data;
    throw new ApiError(errorMessageFromDetail(detail, response.status), response.status);
  }

  if (!response.body?.getReader) {
    throw new ApiError("Streaming is not supported by this browser.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let metadata = {};
  let finalPayload = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parsed = parseSseFrames(buffer);
    buffer = parsed.remainder;
    parsed.completeFrames.forEach((frame) => {
      const { event, data } = parseSseFrame(frame);
      if (event === "progress") {
        callbacks.onProgress?.(data || {});
      } else if (event === "metadata") {
        metadata = data || {};
        callbacks.onMetadata?.(metadata);
      } else if (event === "token") {
        callbacks.onToken?.(data?.text || "");
      } else if (event === "done") {
        finalPayload = data || {};
      } else if (event === "error") {
        throw new ApiError(data?.message || "Streaming generation failed.", data?.status || 500);
      }
    });
  }

  if (!finalPayload) {
    throw new ApiError("Streaming response ended before completion.");
  }
  return { ...metadata, ...finalPayload };
}

export function uploadDocument(
  apiKey,
  conversationId,
  file,
  conversationSettings = null,
) {
  const formData = new FormData();
  formData.append("conversationId", conversationId);
  if (conversationSettings) {
    formData.append("conversationSettings", JSON.stringify(conversationSettings));
  }
  formData.append("file", file);

  return request("/documents/upload", {
    method: "POST",
    apiKey,
    formData,
  });
}

export function processDocument(
  apiKey,
  documentId,
  conversationId,
  conversationSettings = null,
) {
  return request(`/documents/${encodeURIComponent(documentId)}/process`, {
    method: "POST",
    apiKey,
    body: {
      conversationId,
      conversationSettings,
    },
  });
}

export function startProcessDocumentJob(
  apiKey,
  documentId,
  conversationId,
  conversationSettings = null,
) {
  return request(`/documents/${encodeURIComponent(documentId)}/process/jobs`, {
    method: "POST",
    apiKey,
    body: {
      conversationId,
      conversationSettings,
    },
  });
}

export function listDocuments(apiKey, conversationId) {
  const params = new URLSearchParams({ conversationId });
  return request(`/documents?${params.toString()}`, { apiKey });
}

export function getDocument(apiKey, documentId, conversationId) {
  const params = new URLSearchParams({ conversationId });
  return request(
    `/documents/${encodeURIComponent(documentId)}?${params.toString()}`,
    { apiKey },
  );
}

export function getDocumentChunks(apiKey, documentId, conversationId) {
  const params = new URLSearchParams({ conversationId });
  return request(
    `/documents/${encodeURIComponent(documentId)}/chunks?${params.toString()}`,
    { apiKey },
  );
}

export function indexDocument(
  apiKey,
  documentId,
  conversationId,
  conversationSettings = null,
) {
  return request(`/documents/${encodeURIComponent(documentId)}/index`, {
    method: "POST",
    apiKey,
    body: {
      conversationId,
      conversationSettings,
    },
  });
}

export function startIndexDocumentJob(
  apiKey,
  documentId,
  conversationId,
  conversationSettings = null,
) {
  return request(`/documents/${encodeURIComponent(documentId)}/index/jobs`, {
    method: "POST",
    apiKey,
    body: {
      conversationId,
      conversationSettings,
    },
  });
}

export function getJob(apiKey, jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}`, { apiKey });
}

export function cancelJob(apiKey, jobId) {
  return request(`/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: "POST",
    apiKey,
  });
}

export function searchDocuments(
  apiKey,
  conversationId,
  query,
  conversationSettings = null,
  { documentIds = [], topK = 5 } = {},
) {
  return request("/documents/search", {
    method: "POST",
    apiKey,
    body: {
      conversationId,
      query,
      conversationSettings,
      documentIds,
      topK,
    },
  });
}

export function listDocumentIndexes(apiKey, conversationId) {
  const params = new URLSearchParams({ conversationId });
  return request(`/documents/indexes?${params.toString()}`, { apiKey });
}

export function deleteDocumentIndex(apiKey, collectionId, conversationId) {
  const params = new URLSearchParams({ conversationId });
  return request(
    `/documents/indexes/${encodeURIComponent(collectionId)}?${params.toString()}`,
    {
      method: "DELETE",
      apiKey,
    },
  );
}

export function indexLocalRepository(apiKey, path) {
  return request("/repos/index-local", {
    method: "POST",
    apiKey,
    body: { path },
  });
}

export function askRepository(apiKey, repoName, question) {
  return request("/repos/ask", {
    method: "POST",
    apiKey,
    body: { repo_name: repoName, question },
  });
}
