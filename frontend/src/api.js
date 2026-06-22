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

async function request(path, { method = "GET", apiKey = "", body } = {}) {
  const headers = {};

  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers,
      credentials: "include",
      body: body === undefined ? undefined : JSON.stringify(body),
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

export function switchModel(model) {
  return request("/models/switch", {
    method: "POST",
    body: { model },
  });
}

export function sendChat(apiKey, message, history = []) {
  return request("/chat", {
    method: "POST",
    apiKey,
    body: { message, history },
  });
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
