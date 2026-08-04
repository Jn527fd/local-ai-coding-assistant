import { createApiClient } from "./client"

export const API_BASE_URL = normalizeApiBaseUrl(
  import.meta.env.VITE_API_BASE_URL,
)

export const apiClient = createApiClient({
  baseUrl: API_BASE_URL,
  // Phase 4 can replace this with the session provider's token accessor.
  getAccessToken: () => null,
})

export function normalizeApiBaseUrl(value: unknown): string {
  if (typeof value !== "string") return "/api"
  const trimmed = value.trim()
  if (!trimmed || trimmed.toLowerCase() === "auto") return ""
  return trimmed
}

export { createApiClient } from "./client"
export type { ApiClient, ApiClientOptions, ApiRequestOptions } from "./client"
