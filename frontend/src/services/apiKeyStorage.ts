export const API_KEY_STORAGE_KEY = "local-ai-coding-assistant.api-key"

export interface ApiKeyStorage {
  get(): string
  set(apiKey: string): void
}

export function createBrowserApiKeyStorage(
  storageKey = API_KEY_STORAGE_KEY,
): ApiKeyStorage {
  return {
    get() {
      try {
        return globalThis.localStorage?.getItem(storageKey) ?? ""
      } catch {
        return ""
      }
    },
    set(apiKey) {
      try {
        globalThis.localStorage?.setItem(storageKey, apiKey)
      } catch {
        // The app remains usable if browser storage is restricted.
      }
    },
  }
}
